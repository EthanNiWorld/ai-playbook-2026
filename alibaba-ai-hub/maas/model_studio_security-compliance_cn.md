# 百炼平台安全合规评估应答

### 1. 算力隔离与计算安全

#### 1.1 底层隔离形态

百炼通过安全容器实现租户间的严格隔离，不同用户的计算、存储、网络资源互不干扰。底层结合阿里云袋鼠安全容器和 cGPU 虚拟 GPU 隔离技术，确保多租户环境下的资源隔离。

📎 参考：
- [阿里云百炼安全白皮书](https://developer.aliyun.com/ebook/8490)
- [cGPU 容器共享技术](https://help.aliyun.com/zh/egs/what-is-cgpu)

#### 1.2 侧信道攻击与虚拟化逃逸

✅ 支持。百炼在虚拟化层提供安全防护，采用纵深防御 + 零信任架构。


📎 参考：
- [阿里云百炼安全白皮书](https://developer.aliyun.com/ebook/8490)

#### 1.3 推理结束后内存清零

✅ 支持。百炼推理过程数据不持久化，推理结束后内存自动释放。

📎 参考：[阿里云百炼安全白皮书](https://developer.aliyun.com/ebook/8490)

#### 1.4 多租户推理隔离
✅ 支持。百炼通过 Workspace（业务空间）实现多租户数据隔离。

主账号可以给不同子账号分配不同的业务空间，空间之间数据互不可见。超级管理员可按模型维度控制调用、训练、部署权限，并可设置请求数和 Token 数的限流阈值。推理过程数据不持久化，技术上不存在跨租户串扰的路径。

📎 参考：
- [权限管理](https://help.aliyun.com/zh/model-studio/permission-management-overview)
- [常见问题](https://help.aliyun.com/zh/model-studio/faq-about-alibaba-cloud-model-studio)

---

### 2. 运维权限与明文访问管控

✅ 支持。所有运维操作必须走堡垒机（Bastion Host）+ 双因素认证（2FA），无例外通道。堡垒机上的每一步操作均被实时记录并同步到中央日志平台。访问物理服务器或虚拟机需提前申请、审批，设好访问期限，到期自动回收权限。

关于客户数据：阿里云遵循"未经客户同意不访问"原则，所有访问行为留痕可审计。

📎 参考：[阿里云安全合规实践](https://security.aliyun.com/trust-center/practices)

---

### 3. 数据销毁与残留风险

#### 3.1 数据销毁证明

✅ 支持。阿里云对退役存储介质执行标准流程：敏感数据多次覆写擦除，不需要的介质进行物理粉碎，全程记录存档可审计。用户主动删除或服务期满后，自动触发清除程序。百炼推理数据可单独出具销毁证明。

#### 3.2 系统自动备份留存周期

✅ 支持。根据法律法规要求，百炼会存储模型与应用调用时产生的数据，详细留存周期与处理规则见《阿里云百炼服务协议》。

📎 参考：
- [阿里云安全合规实践](https://security.aliyun.com/trust-center/practices)
- [阿里云百炼服务协议](https://terms.alicdn.com/legal-agreement/terms/common_platform_service/20230728213935489/20230728213935489.html)

---

### 4. 模型安全与审计能力

### 4.1 SOC 2 认证

✅ 已通过 SOC 2 Type II 审计，无保留意见。审计覆盖安全性、可用性和保密性三个信托原则，每年出两次报告，审计期间连续滚动 12 个月。签 NDA 后可从合规文档中心下载报告。

其他已获得的认证：
- ISO/IEC 42001 人工智能管理体系认证（全球首张）
- 中国信通院大模型安全认证
- 模型备案信息已在平台公示

算法备案、伦理合规等证明材料均可通过合规文档中心获取。

📎 参考：
- [合规资质与隐私说明](https://help.aliyun.com/zh/model-studio/privacy-notice)
- [SOC 报告下载](https://help.aliyun.com/zh/document_detail/2928445.html)
- [合规文档中心](https://security.aliyun.com/compliance-repository)
- [阿里云百炼安全白皮书](https://developer.aliyun.com/ebook/8490)

#### 4.2 数据不进入模型训练

✅ 支持。阿里云承诺不会将客户数据用于模型训练。传输过程采用 AES-256 加密，存储支持 BYOK（用户自带密钥）。


📎 参考：
- [阿里云百炼安全白皮书](https://developer.aliyun.com/ebook/8490)
- [合规资质与隐私说明](https://help.aliyun.com/zh/model-studio/privacy-notice)

#### 4.3 模型接入管控

✅ 支持，百炼有模型白名单机制。

超级管理员可以在业务空间里按模型维度做精细管控：哪些模型允许调用、哪些允许训练、哪些允许部署，都可以单独控制，还能设请求数和 Token 数的限流阈值。


📎 参考：[权限管理](https://help.aliyun.com/zh/model-studio/permission-management-overview)

---

### 5. 跨境访问与网络边界

#### 5.1 Geo-fencing

✅ 平台原生支持 Geo-fencing 能力。百炼通过地域 + 服务部署范围的组合控制数据驻留：

| 场景 | 地域 | 部署范围 |
|------|------|---------|
| 数据不出中国内地 | 华北2（北京） | 中国内地 |
| 数据不出中国香港 | 中国香港 | 中国香港 |
| 数据不出美国 | 美国（弗吉尼亚） | 美国 |
| 数据不出欧盟 | 德国（法兰克福） | 欧盟 |
| 数据不出日本 | 日本（东京） | 日本 |

推理过程数据不持久化，传输全程加密，用户静态数据只存在选定地域内。

📎 参考：[地域与服务部署范围](https://www.alibabacloud.com/help/zh/model-studio/regions/)

#### 5.2 全链路境内保障

✅ 支持，提供了传输加密和私网访问两种手段。

传输层走 HTTPS/TLS，应用层支持 AES+RSA 混合加密（SDK 里一行 `enableEncrypt=true` 就能开）。如果需要完全不走公网，可以通过 PrivateLink 在 VPC 内网直接调百炼 API。生产环境建议用专属域名，并发承载能力和网络隔离性都更好。

📎 参考：
- [传输安全](https://help.aliyun.com/zh/model-studio/transmission-security/)
- [加密调用](https://help.aliyun.com/zh/model-studio/encrypted-access-to-model-inference)
- [PrivateLink 私网访问](https://help.aliyun.com/zh/model-studio/access-model-studio-through-privatelink)

---

### 6. 服务保障与数据完整性

#### 6.1 SLA

✅ 99.9%（专属域名和共享域名都有 SLA，试用域名不提供）。

| 对比项 | 专属域名 | 共享域名 | 试用域名 |
|--------|:---:|:---:|:---:|
| SLA | 99.9% | 99.9% | 不提供 |
| 请求超时 | 3600s | 600s | 600s |

共享算力下如遇资源抢占导致中断，可通过以下方式兜底：启用专属域名、在业务空间设 Token 限流控制调用速率、关键任务加指数退避和自动重试。

百炼支持 PTU / Model Unit / TPM 预留等模式，可保障 TPM 等核心吞吐指标。

📎 参考：
- [相关协议](https://help.aliyun.com/zh/model-studio/related-agreements)
- [地域与接入域名](https://www.alibabacloud.com/help/zh/model-studio/regions/)

#### 6.2 数据签名验签 / 哈希校验

百炼通过以下多层机制保障数据完整性：传输层 TLS 保完整性、应用层 AES 加密防篡改、API 请求走 AK/SK 签名验证、操作审计通过 ActionTrail 记录请求和响应日志。

如需独立的完整性证明，可通过 ActionTrail 审计日志 + 传输层加密的组合满足合规审计要求。

📎 参考：
- [加密调用](https://help.aliyun.com/zh/model-studio/encrypted-access-to-model-inference)
- [AI 网关鉴权](https://help.aliyun.com/zh/api-gateway/ai-gateway/product-overview/what-is-an-ai-gateway)


## 数据源
- [阿里云百炼安全白皮书（2025云栖大会发布，59页7章）](https://developer.aliyun.com/ebook/8490)
- https://help.aliyun.com/zh/model-studio/
- https://www.alibabacloud.com/help/zh/model-studio/
- https://security.aliyun.com/trust-center/practices
- https://help.aliyun.com/zh/model-studio/privacy-notice
- https://terms.alicdn.com/legal-agreement/terms/common_platform_service/20230728213935489/20230728213935489.html
