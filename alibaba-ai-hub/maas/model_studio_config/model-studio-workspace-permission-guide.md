# 百炼业务空间权限管理指南 (Alibaba Cloud Model Studio - International)

## 问题场景

访问阿里云百炼（Alibaba Cloud Model Studio）时提示：**"You do not have access permissions to this workspace, or the workspace does not exist"**

## 原因说明

百炼业务空间通过权限点对页面进行管理。当用户未被授予相应业务空间的访问权限时，会显示此提示信息。

即使 RAM 用户拥有全局管理权限（如 `AliyunBailianFullAccess`），也需要单独为每个业务空间添加成员权限才能访问该空间。

## 解决方案

管理员需要按以下步骤完成授权操作：

### 步骤 1：进入目标业务空间

- 在阿里云百炼控制台首页左下角，点击图标切换到目标业务空间
- 支持的地域包括：**新加坡（Singapore）**、**北京（Beijing）**等

 参考：[Manage workspace members - Alibaba Cloud Documentation](https://www.alibabacloud.com/help/en/model-studio/member-management)

---

### 步骤 2：添加 RAM 用户作为业务空间成员

在左侧导航栏中，点击 **Permissions（权限管理）**，找到目标 RAM 用户，点击其右侧的 **Permissions（权限管理）**。

**重要说明：**
- 必须先将 RAM 用户添加为业务空间的成员，其才能访问（只读）该空间的功能页面及数据
- 阿里云百炼不会自动添加 RAM 用户到任何业务空间，需要手动添加
- 暂不支持批量添加和邀请

**支持的授权对象：**
- RAM 用户（子账号）
- RAM 角色（服务角色、跨账号角色等）

---

### 步骤 3：配置成员的 4 种权限类型

加入业务空间的 RAM 用户可获取 4 种权限类型，彼此互不重叠，请按需配置：

#### 3.1 模型权限（Model Permissions）

**默认业务空间：**
- RAM 用户加入默认业务空间后可直接调用、调优和部署所有支持的模型，无需额外授权

**子业务空间：**
- 初始状态下子业务空间无任何模型调用、调优或部署权限
- 需要在 **Authorization & Throttling Settings（授权与流控设置）** 中为目标模型开启相应权限
- 操作路径：Workspaces → 找到目标业务空间 → Authorization & Throttling Settings → Edit → 开启所需权限 → Save

**支持的权限粒度：**
- 模型调用权限：允许调用哪些模型（如 qwen-plus、qwen-max 等）
- 模型训练权限：允许进行模型微调训练
- 模型部署权限：允许部署私有化模型
- 资源限额控制：设置请求数和 Token 数的限流阈值

#### 3.2 页面权限（Page Permissions）

**默认权限：**
- RAM 用户在加入的业务空间中，默认仅拥有除系统管理、权限管理及密钥管理外所有功能页面的**只读权限**

**完整功能权限：**
- 若需使用特定页面（如知识库、Prompt 工程等）的完整功能（包括新建、删除和编辑等写入类操作），需在 **Page Permissions** 区域点击 **Edit**，勾选需要的功能页面操作权限
- 建议仅授予用户完成其任务所必需的权限（最小权限原则）

#### 3.3 API 权限（API Permissions）

**默认权限：**
- RAM 用户在加入的业务空间中，默认**无权调用**应用数据、知识库、Prompt 工程及长期记忆等功能的接口

**启用 API 权限：**
- 如需调用这些功能的 API，需要手动添加相应的 API 权限
- 注意：API Key 的可调用功能和模型限流与归属业务空间的权限保持一致，不受用户控制台权限管理的影响

#### 3.4 管理权限（Management Permissions）

**系统管理权限：**
- 默认情况下，RAM 用户无法访问 System Administration 页面，因此不能管理任何 Model Studio 工作空间、账号或 API Key
- 如需授权全局管理操作，需要在 RAM 控制台为用户添加 `AliyunBailianFullAccess` 系统策略
- 注意：管理权限（全局管理）仅授予 RAM 用户执行跨工作空间的管理操作能力，不包含对任何具体工作空间的访问权限

📎 参考：
- [Member management - Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/member-management)
- [Permission management overview](https://help.aliyun.com/zh/model-studio/permission-management-overview)

---

## 完成授权后

- 被授权用户刷新页面后即可正常访问该业务空间
- 权限变更实时生效

---

## 多租户数据隔离机制

百炼通过 **Workspace（业务空间）** 实现多租户数据隔离：

✅ **主账号可以给不同子账号分配不同的业务空间**  
✅ **空间之间数据互不可见**  
✅ **超级管理员可按模型维度控制调用、训练、部署权限**  
✅ **可设置请求数和 Token 数的限流阈值**  
✅ **推理过程数据不持久化，技术上不存在跨租户串扰的路径**

**重要安全提示：**
- 如果将默认业务空间的 API Key 共享给子业务空间中的 RAM 用户，用户可以绕过工作空间授权直接通过 API 调用模型
- 虽然技术上可行，但这可能引入安全风险，应避免这种做法

📎 参考：[Security and compliance](https://help.aliyun.com/zh/model-studio/security-compliance)

---

## 常见问题

### Q1：如何查看我已拥有的业务空间？

A：登录百炼控制台后，在左下角点击切换图标，即可查看当前账号有权限访问的所有业务空间列表。支持的地域包括新加坡、北京等。

### Q2：我有管理权限（AliyunBailianFullAccess），但为什么还是看到 "You do not have access permissions to this workspace" 错误？

A：`AliyunBailianFullAccess` 系统策略仅允许 RAM 用户访问 System Administration 页面，不包含对任何工作空间的访问权限。要访问工作空间，用户必须获得该工作空间的成员权限（member permissions）。

### Q3：如果我是超级管理员，如何给团队成员授权？

A：
1. 在百炼控制台首页左下角切换到目标业务空间
2. 在左侧导航栏点击 **Permissions（权限管理）**
3. 添加团队成员的 RAM 账号作为业务空间成员
4. 根据团队职责配置相应的权限：
   - 模型权限：在 Authorization & Throttling Settings 中开启对应模型的调用/训练/部署权限
   - 页面权限：在 Page Permissions 中勾选需要的功能页面操作权限
   - API 权限：如需调用应用数据、知识库等功能 API，需手动添加相应权限
5. 通知团队成员刷新页面后即可访问

### Q4：权限变更后多久生效？

A：权限变更实时生效，被授权用户刷新页面后即可看到变化。

### Q5：如何撤销某个用户的权限？

A：
1. 切换到目标业务空间
2. 在左侧导航栏点击 **Permissions（权限管理）**
3. 找到目标 RAM 用户，点击其右侧的 **Delete（删除）**
4. 确认删除

**注意：** 此操作会移除 RAM 用户对该业务空间的所有访问和操作权限，同时使该用户在该空间中创建的任何 API Key 失效。用户在其他工作空间中的权限和 API Key 不受影响。

### Q6：RAM 用户在子业务空间中调用 API 时收到 AccessDenied 错误怎么办？

A：检查以下几点：
1. 确认该子业务空间已获得目标模型的调用权限（在 Authorization & Throttling Settings 中查看）
2. 确认使用的 API Key 属于正确的业务空间
3. 如果使用 Claude Code 等工具报错，建议使用默认业务空间的 API Key
4. 刷新数据、重新发布后再尝试调用，或重新创建 Agent

---

## 相关文档

- [Manage workspace members - Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/member-management)
- [Permission management overview](https://help.aliyun.com/zh/model-studio/permission-management-overview)
- [Get an API Key](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
- [Error messages and troubleshooting](https://www.alibabacloud.com/help/en/model-studio/error-code)
- [RAM user management](https://www.alibabacloud.com/help/en/ram/user-guide/create-a-ram-user)

---

*文档更新时间：2026-06-29*  
*适用产品：Alibaba Cloud Model Studio (International Edition)*  
*支持地域：Singapore, Beijing 等*
