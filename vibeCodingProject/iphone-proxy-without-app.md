# iPhone 免 App 使用 Shadowsocks 代理

## 背景

iPhone 上没有安装任何代理 App（如 Shadowrocket、QuantumltX 等），但需要通过代理访问被封锁的网站。常见方案需要侧载 App 或订阅证书，操作复杂且有失效风险。

## 需求

- iPhone 不安装任何额外 App
- 利用同一局域网内另一台已运行 Shadowsocks 客户端的电脑作为代理中转
- 零成本、零配置门槛

## 架构

```
iPhone                    另一台电脑 (Mac)                阿里云 ECS
(WiFi 代理设置)  ──WiFi──→  SS客户端 (HTTP代理)  ──加密──→  SS服务端  ──→ 互联网
                      192.168.x.x:1087
```

核心思路：iPhone 利用 iOS 系统自带的 WiFi 代理功能，将流量转发到局域网内已运行 Shadowsocks 客户端的电脑，由该电脑通过加密通道转发到远端 ECS 服务器，再由 ECS 访问互联网。

## 前置条件

1. iPhone 和电脑连接在**同一个 WiFi/局域网**
2. 电脑端 Shadowsocks 客户端已连接远端服务器且工作正常
3. 电脑开机且 SS 客户端保持运行

## 配置步骤

### 第一步：Mac 端开启局域网代理访问

ShadowsocksX-NG 的 HTTP 代理组件（privoxy）默认只监听 `127.0.0.1`（仅本机），需要改为监听 `0.0.0.0`（允许局域网访问）。

**方法：** 通过终端操作

```bash
# 1. 杀掉 privoxy 进程
kill $(ps aux | grep privoxy | grep -v grep | awk '{print $2}')

# 2. 修改配置文件监听地址
sed -i '' 's/listen-address 127.0.0.1:1087/listen-address 0.0.0.0:1087/' \
  "$HOME/Library/Application Support/ShadowsocksX-NG/privoxy.config"

# 3. 重启 privoxy
cd "$HOME/Library/Application Support/ShadowsocksX-NG"
./privoxy --no-daemon privoxy.config &

# 4. 验证监听状态（应显示 *:1087）
lsof -i :1087 -P -n | grep LISTEN
```

> **注意：** 必须通过 App 偏好设置修改（偏好设置 → 高级 → HTTP 代理监听地址改为 `0.0.0.0`），或像上面这样先杀进程再改文件再启动，因为 ShadowsocksX-NG 会自动覆盖配置文件。

### 第二步：查询 Mac 局域网 IP

```bash
ifconfig en0 | grep "inet " | awk '{print $2}'
# 输出示例：192.168.155.243
```

### 第三步：iPhone 配置 WiFi 代理

1. 打开 **设置** → **无线局域网**
2. 点击当前连接的 WiFi 名称右侧的 **ⓘ** 图标
3. 滑到底部找到 **HTTP 代理**
4. 选择 **手动**
5. 填写：
   - **服务器**：Mac 的局域网 IP（如 `192.168.155.243`）
   - **端口**：`1087`（ShadowsocksX-NG 默认 HTTP 代理端口）
   - **认证**：关闭
6. 点 **存储**

### 第四步：验证

在 iPhone Safari 中访问 `google.com`，能打开即为成功。

## 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| iPhone 连不上代理 | Mac 防火墙拦截 | 系统设置 → 网络 → 防火墙 → 关闭或放行 1087 端口 |
| 代理连上但无法上网 | SS 客户端未连接 ECS | 确认 Mac 上 SS 客户端状态正常 |
| 只能上部分网站 | SS 客户端处于 PAC/规则模式 | 改为全局模式 |
| 换 WiFi 后失效 | Mac IP 变了 | 重新查 IP，更新 iPhone 代理设置 |

## 方案局限性

- **仅限同一局域网**：iPhone 离开电脑所在 WiFi 即失效
- **电脑必须开机**：代理完全依赖电脑端的 SS 客户端
- **WiFi 代理是全局的**：所有 HTTP/HTTPS 流量都走代理，无法按 App 区分
- **安全性**：局域网内其他设备如果知道 IP 和端口也可以使用代理（家庭/办公室场景风险较低）

## 其他客户端参考

### Windows（Shadowsocks-Windows）

右键托盘图标 → 选项设置 → 勾选 "允许其他设备连入"（Allow other devices to connect），HTTP 代理端口默认 `1089`。

### Clash / mihomo

编辑配置文件：

```yaml
allow-lan: true        # 允许局域网连接
bind-address: '*'      # 绑定所有网卡
mixed-port: 7890       # HTTP+SOCKS 混合端口
```
