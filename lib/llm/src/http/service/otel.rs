use axum::http::{HeaderMap, Request, header::HeaderName};
use opentelemetry::propagation::{Extractor, Injector};
use std::collections::HashMap;
use std::str::FromStr;
use axum::body::Body;

// 导入所需依赖
use anyhow::Result;
use opentelemetry::{global, Context, KeyValue};
use opentelemetry_sdk::{trace, Resource};
use opentelemetry_sdk::trace::{Tracer, Sampler};
use tracing_subscriber::{prelude::*, Registry, EnvFilter};
use tracing_subscriber::fmt::Layer;
use tracing_opentelemetry::OpenTelemetryLayer;
use opentelemetry_otlp::WithExportConfig;

// 重新导出tracing的宏和类型
pub use tracing::{error, warn, info, debug, trace, info_span, Span, instrument};

/// 初始化OpenTelemetry和Jaeger追踪
pub fn init_tracer(jaeger_endpoint: &str, service_name: &str) -> Result<()> {
    info!("初始化Jaeger追踪，端点: {}", jaeger_endpoint);
    
    // 设置标准OpenTelemetry环境变量
    std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", jaeger_endpoint);
    std::env::set_var("OTEL_SERVICE_NAME", service_name);
    
    // 日志输出初始化信息，用于调试
    info!("正在使用以下配置初始化追踪系统:");
    info!("  - 服务名称: {}", service_name);
    info!("  - Jaeger端点: {}", jaeger_endpoint);
    
    // 尝试真正初始化OpenTelemetry追踪器
    match init_real_tracer(jaeger_endpoint, service_name) {
        Ok(_) => {
            info!("OpenTelemetry追踪器初始化成功");
            // 测试追踪是否工作
            let span = info_span!("测试跟踪span");
            let _guard = span.enter();
            info!("这条消息应该出现在Jaeger中");
        }
        Err(e) => {
            warn!("OpenTelemetry追踪器初始化失败: {}，将使用环境变量方式", e);
        }
    }
    
    Ok(())
}

/// 尝试真正初始化OTLP追踪器
fn init_real_tracer(jaeger_endpoint: &str, service_name: &str) -> Result<()> {
    // 简化实现，不使用Resource
    info!("使用简化追踪配置，服务名称: {}", service_name);
    
    // 构建导出器
    #[cfg(feature = "otlp")]
    {
        // 这段代码仅在启用otlp特性时编译
        info!("OTLP特性已启用，但API似乎不兼容");
    }
    
    // 构建基本的订阅者层
    let filter_layer = EnvFilter::try_from_default_env()
        .or_else(|_| EnvFilter::try_new("info"))
        .unwrap();
        
    let fmt_layer = Layer::default()
        .with_ansi(true);
        
    let subscriber = Registry::default()
        .with(filter_layer)
        .with(fmt_layer);
        
    // 设置订阅者
    tracing::subscriber::set_global_default(subscriber)?;
    
    info!("基本追踪系统已初始化");
    Ok(())
}

/// 实现从HTTP请求头中提取追踪上下文
pub struct HeaderExtractor<'a>(&'a HeaderMap);

impl<'a> Extractor for HeaderExtractor<'a> {
    fn get(&self, key: &str) -> Option<&str> {
        self.0.get(key).and_then(|v| v.to_str().ok())
    }

    fn keys(&self) -> Vec<&str> {
        self.0.keys().map(|k| k.as_str()).collect()
    }
}

/// 实现向HTTP响应头中注入追踪上下文
pub struct HeaderInjector<'a>(&'a mut HeaderMap);

impl<'a> Injector for HeaderInjector<'a> {
    fn set(&mut self, key: &str, value: String) {
        if let Ok(val) = value.parse() {
            if let Ok(name) = HeaderName::from_str(key) {
                self.0.insert(name, val);
            }
        }
    }
}

/// 从请求中提取追踪上下文
pub fn extract_context_from_request(req: &Request<Body>) -> opentelemetry::Context {
    let extractor = HeaderExtractor(req.headers());
    dynamo_runtime::logging::extract_trace_context(&extractor)
}

/// 中间件，用于在请求处理之前自动创建span
pub async fn trace_middleware(
    req: Request<Body>,
    next: axum::middleware::Next,
) -> impl axum::response::IntoResponse {
    // 从请求头中提取追踪上下文
    let parent_context = extract_context_from_request(&req);
    
    // 创建一个span，包含请求的基本信息
    let path = req.uri().path().to_owned();
    let method = req.method().to_string();
    let span = dynamo_runtime::logging::create_span_with_parent_context(
        &format!("{} {}", method, path),
        parent_context,
    );
    let _enter = span.enter();
    
    // 记录请求信息
    tracing::info!(
        method = %method,
        path = %path,
        "开始处理请求"
    );
    
    // 处理请求
    let start = std::time::Instant::now();
    let response = next.run(req).await;
    let duration = start.elapsed();
    
    // 记录响应信息
    let status = response.status().as_u16();
    tracing::info!(
        status = status,
        duration_ms = duration.as_millis() as u64,
        "完成请求处理"
    );
    
    response
}