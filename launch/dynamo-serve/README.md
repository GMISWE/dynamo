# Dynamo Serve Wrapper

这是一个简单的Rust包装器，允许你使用`cargo run`来运行Dynamo的`dynamo serve`命令。

## 使用方法

### 直接使用cargo run

```bash
# 从Dynamo根目录运行
cd /path/to/dynamo
cargo run --bin dynamo-serve -- <dynamo serve参数>

# 例如，运行LLM示例
cargo run --bin dynamo-serve -- graphs.agg:Frontend -f ./examples/llm/configs/agg.yaml
```

### 创建别名（可选）

在你的`.bashrc`或`.zshrc`中添加以下行，使命令更简洁：

```bash
alias cargo-serve='cd /path/to/dynamo && cargo run --bin dynamo-serve --'
```

然后你可以简单地使用：

```bash
cargo-serve graphs.agg:Frontend -f ./examples/llm/configs/agg.yaml
```

## 环境变量

这个包装器会自动尝试检测和设置`DYNAMO_HOME`环境变量。如果自动检测不正确，你可以手动设置：

```bash
export DYNAMO_HOME=/path/to/dynamo
cargo run --bin dynamo-serve -- <dynamo serve参数>
```

## 故障排除

如果遇到问题，请确保：

1. Python环境已正确设置
2. 所有必要的依赖项已安装
3. `PYTHONPATH`已正确设置（如果需要） 