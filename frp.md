# 内网穿透实战指南 —— frp（v0.50+）HTTP & TCP 服务映射

本文档示例基于 frp v0.50.0 及以上版本，完成以下功能：
1. HTTP 服务（本地 80 端口）映射到公网 8080，支持 Host 校验。
2. 自定义 TCP 服务（本地 5005，服务名 `scott5`）映射到公网 9090。
3. 开启 `token` 鉴权，防止未授权连接。
4. 关闭 dashboard 面板。

---

## 一、环境准备

- 公网服务器（Linux），已下载并解压 frp 包，包含 `frps` 与 `frpc` 可执行文件。
- 内网客户端（Linux）同版本 frp，可执行 `frpc`。
- 公网服务器安全组/防火墙已放通：7000（frp 握手端口）、8080、9090。

---

## 二、服务端配置 —— `frps.ini`

在**公网服务器**上，创建文件 `frps.ini`，内容如下：

```ini
# frps.ini (服务器端)
[common]
# 1. frps 监听端口，frpc 会与此端口建立长连接
bind_port = 7000

# 2. token 鉴权：客户端必须与此处一致，否则无法接入
token = your_secure_token_here

# 3. 关闭 dashboard（默认已禁用），若不需要可留空或注释
# dashboard_port = 7500
# dashboard_user = admin
# dashboard_pwd  = password
```

启动命令（在 `frps` 所在目录执行）：

```bash
./frps -c ./frps.ini
```

> **说明**  
> - `bind_port`：frp 服务端对外开放的握手端口，客户端通过它来注册和心跳。  
> - `token`：最基础的鉴权方式，防止他人任意接入你的 frp 服务。

---

## 三、客户端配置 —— `frpc.ini`

在**内网客户端**上，创建文件 `frpc.ini`，内容如下：

```ini
# frpc.ini (客户端)
[common]
# 1. 指定公网服务器的地址和端口，注意 server_addr 要填公网可访问 IP/域名
server_addr = x.x.x.x
server_port = 7000

# 2. 与 frps.ini 中的 token 保持一致
token = your_secure_token_here

# ----------------------------
# 以下开始业务隧道配置
# ----------------------------

# 映射 1：HTTP 服务
# 使用 type = http，可自动处理 Host 路由，并支持自定义域名（可选）
[http-service]
type        = http
# 本地 HTTP 服务监听地址
local_ip    = 127.0.0.1
local_port  = 80
# 公网访问： http://x.x.x.x:8080
# remote_port 用于指定映射端口，开启端口转发
remote_port = 8080

# 如果你有自己的域名可以这样写（可选）：
# custom_domains = www.yourdomain.com

# 映射 2：scott5 自定义 TCP 服务
[scott5]
type        = tcp
# 本地 scott5 服务监听
local_ip    = 127.0.0.1
local_port  = 5005
# 公网访问： tcp://x.x.x.x:9090
remote_port = 9090
```

启动命令（在 `frpc` 所在目录执行）：

```bash
./frpc -c ./frpc.ini
```

> **说明**  
> - `type = http`：专门处理 HTTP 协议，支持路径、Host 路由和 Header 转发，比 `tcp` 更智能。  
> - `type = tcp`：最基础的 TCP 隧道，适用于任意自定义二进制协议。  
> - `remote_port`：在公网服务器上开放的端口，请确保不被防火墙或其他服务占用。

---

## 四、访问示例

1. **HTTP 服务**  
   浏览器打开：  
   ```
   http://x.x.x.x:8080
   ```
   将会访问到内网 `127.0.0.1:80` 上运行的 Web 服务。

2. **scott5 服务（TCP）**  
   任意 TCP 客户端连接：  
   ```bash
   nc x.x.x.x 9090
   ```  
   或者你自己写的客户端，都会被转发到内网 `127.0.0.1:5005`。

---

## 五、常见问题排查

- **端口冲突**：`bind_port` 与 `remote_port` 请勿与服务器上已有服务冲突。  
- **防火墙/安全组**：务必放通对应端口（7000、8080、9090）。  
- **版本兼容**：服务端与客户端请使用相同的 frp 版本。  
- **日志查看**：`frps` / `frpc` 会在控制台打印日志，定位映射失败或心跳异常。  

---

## 六、附录：命令汇总

```bash
# 1. 服务端启动
cd /path/to/frp
./frps -c frps.ini

# 2. 客户端启动
cd /path/to/frp
./frpc -c frpc.ini
```

至此，你已成功完成 HTTP 与自定义 TCP 服务的内网穿透，并通过 `token` 机制确保基本安全。  
祝使用顺利！
