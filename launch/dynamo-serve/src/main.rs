// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use std::env;
use std::process::Command;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 收集命令行参数
    let args: Vec<String> = env::args().skip(1).collect();
    
    // 确保DYNAMO_HOME环境变量设置正确
    let dynamo_home = env::var("DYNAMO_HOME").unwrap_or_else(|_| {
        // 如果未设置，默认使用当前工作目录
        let current_dir = env::current_dir().expect("Failed to get current directory");
        let path = current_dir.to_string_lossy().to_string();
        
        // 检查路径是否以/dynamo结尾，以避免在容器内被错误识别
        if path.ends_with("/dynamo") {
            return path;
        }
        
        // 否则检查是否在rust/dynamo目录结构中
        if let Some(idx) = path.find("/rust/dynamo") {
            return path[..idx + 12].to_string();
        }
        
        path
    });
    
    println!("Using DYNAMO_HOME: {}", dynamo_home);
    
    // 确定要检查模块所在的工作目录
    let working_dir = format!("{}/examples/llm", dynamo_home);
    println!("Working directory: {}", working_dir);
    
    // 设置环境变量
    let mut cmd = Command::new("python");
    
    // 设置PYTHONPATH以确保可以导入modules
    // 包括当前工作目录和Python SDK目录
    let python_path = format!("{}:{}:{}",
                              working_dir,
                              format!("{}/deploy/dynamo/sdk/src", dynamo_home),
                              env::var("PYTHONPATH").unwrap_or_else(|_| String::new()));
    
    // 构建并执行命令
    cmd.current_dir(&working_dir) // 切换到工作目录
       .arg("-m")
       .arg("dynamo.sdk.cli.cli")
       .arg("serve")
       .args(&args)
       .env("DYNAMO_HOME", &dynamo_home)
       .env("PYTHONPATH", &python_path);
    
    println!("执行命令: python -m dynamo.sdk.cli.cli serve {}", args.join(" "));
    println!("工作目录: {}", working_dir);
    println!("PYTHONPATH: {}", python_path);
    
    // 执行命令
    let status = cmd.status()?;
    
    // 检查命令执行状态
    if !status.success() {
        std::process::exit(status.code().unwrap_or(1));
    }
    
    Ok(())
} 