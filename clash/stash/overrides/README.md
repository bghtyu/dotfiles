# Stash 可选覆写

三个现成 Stash 覆写的独立适配文件，只用于 Stash。主配置 `clash/stash.yaml` 和 FlClash 配置、代理、DNS、分组、分流及生成器均不改变；导入主配置不会自动加载这些文件。无 YouTube 覆写。

| 文件 | 来源 | 功能与边界 |
| --- | --- | --- |
| [bilibili.stoverride](bilibili.stoverride) | [Biliverse ADBlock v0.7.5](https://github.com/Biliverse/ADBlock/releases/download/v0.7.5/BiliBili.ADBlock.stoverride) | 开屏、推荐、搜索、动态、播放页等广告及界面净化；保留上游默认偏好和 BoxJS 配置入口，通常无需 BoxJS 即可使用。已移除非广告用途的 `Teenagers/ModeStatus` 青少年模式弹窗处理，省略上游空 `argument` 字段（官方定义类型为字符串）。 |
| [wx110.stoverride](wx110.stoverride) | [qsoyq wx110](https://github.com/qsoyq/shell/blob/29d9e686c29a5b22f4ca6239c73dc035ad808c2f/config/stash/override/ad/wx110.stoverride) | 墨鱼 weixin110 脚本，匹配微信外链提示页，提取链接并发通知，用户点击到浏览器打开；不保证所有链接均可打开，也不判定链接安全。仅支持该脚本识别的页面结构，Stash 通知权限需开启。 |
| [rednote.stoverride](rednote.stoverride) | [HotKids RedNote](https://github.com/HotKids/Rules/blob/e8970451207e555d7fc8005ca9df9b3bb5821564/Surge/Module/Stash/RedNote.stoverride) / fmz200 | 开屏、搜索、首页等广告与界面净化；还包含图片/视频/评论区去水印和下载处理、信息流直播/带货/商品过滤、保存及画质相关设置、评论 `red_id` 字段改名为 `fmz200`、媒体下载作者字段设置为 `@fmz200`，并持久化媒体链接，并非只去广告。 |

## 导入与独立开关

1. 使用已经填入自己订阅的 Stash 主配置。在 Stash 的覆写管理中，分别从文件导入上述三个 `.stoverride`，或使用以下本仓库地址（**主分支地址需 PR 合并后才可下载**；合并前可下载本 PR 分支中的文件，本地导入）。它们是覆写，不是完整代理配置。

   - `https://raw.githubusercontent.com/bghtyu/dotfiles/main/clash/stash/overrides/bilibili.stoverride`
   - `https://raw.githubusercontent.com/bghtyu/dotfiles/main/clash/stash/overrides/wx110.stoverride`
   - `https://raw.githubusercontent.com/bghtyu/dotfiles/main/clash/stash/overrides/rednote.stoverride`

2. 初次只启用一个，确认无同类脚本覆写重复启用；检查最终有效配置的 `http.mitm`、`http.script` 和 `script-providers`。三个文件可以各自开关；不含 `#!replace`，按 Stash 默认规则递归合并字典、将数组插入原数组前方，互不覆盖各自的 HTTP 规则。若还启用了其他覆写，应单独核对最终合并结果。
3. HTTPS 内容改写需要**本机 Stash CA**。由用户在设备的 Stash → MitM → CA 证书生成自己的 CA，按系统提示安装，再在 iOS 设置 → 通用 → 关于本机 → 证书信任设置中信任该 CA；由用户决定是否启用设备上的 MitM。不要下载、导入或信任任何共享 CA，不要将证书、私钥、密码提交或分享。仓库不提供 CA、证书密码，也不关闭 TLS 验证。
4. 启用后检查脚本下载成功，依次测试登录、首页、搜索、视频/直播播放，以及微信外链通知，核对 Stash 日志。异常时关闭对应覆写并重连；若响应被 App 缓存，关闭后可能还需重启 App/清理相关缓存。不要为了去广告直接重装或清除全部个人数据。
5. 停用这些功能时，关闭对应覆写；全部停用后可关闭 MitM，并由用户决定移除设备上的 CA 信任/描述文件。共享脚本持久化或 App 缓存不会因关闭覆写自动清除。

## HTTPS 解密范围

启用后 Stash 可读取并改写下列精确主机的 HTTPS 内容，包括其中可能出现的账号、请求参数、链接和响应数据。脚本具有 Stash 脚本 API 权限；域名列表限定 HTTP 触发范围，不是脚本能力沙箱或联网白名单。未添加任何域名通配符。

- **B 站（13）**：`biliverse.github.io`、`manga.bilibili.com`、`api.live.bilibili.com`、`api.vc.bilibili.com`、`app.bilibili.com`、`app.biliapi.net`、`app.biliapi.com`、`api.bilibili.com`、`api.biliapi.net`、`grpc.biliapi.net`、`cm.bilibili.com`、`adtrack.qianwen.com`、`tkio-redirect.solar-engine.com`。其中 Biliverse 域名用于偏好配置入口；后两项为上游广告跟踪接口，并非代理路由规则。
- **微信（2）**：`weixin110.qq.com`、`security.wechat.com`。仅匹配 `newredirectconfirmcgi` 页面，已修正上游正则中未转义的域名点。脚本参数固定 `useCache=false&forceRedirect=false`，覆盖同名持久化偏好，不自动访问归档快照，也不强制循环跳转；上游参数解析将 `true` 拼为 `ture` 的缺陷仍存在于固定脚本中，本配置不依赖该功能。打开通知会将原链接交给外部浏览器。
- **小红书（10）**：`edith.xiaohongshu.com`、`www.xiaohongshu.com`、`ci.xiaohongshu.com`、`rec.xiaohongshu.com`、`so.xiaohongshu.com`、`edith.rnote.com`、`www.rnote.com`、`ci.rnote.com`、`so.rnote.com`、`rec.rnote.com`。已删除上游全部 `rules`：四项广告域名 REJECT 和覆盖整个 `xiaohongshu.com` 的 QUIC REJECT，保持主配置的流量路由；因此效果可能弱于原版，特别是 App 使用 QUIC 时。不会自动增加广泛协议阻断。

## 来源、固定版本与更新

[sources.json](sources.json) 记录 2026-11-05 实际获取成功的覆写来源、完整提交、上游/本地 SHA-256、每个唯一脚本 URL 的大小和 SHA-256，以及本地调整。配置中保留上游作者信息；这些第三方配置和脚本的权利仍属于各自作者，不因本仓库许可而重新授权。未在仓库复制或执行远程 JS。

B 站的三个唯一 bundle 使用固定 `v0.7.5` release URL；微信脚本固定墨鱼 `97b8abea5ff52b5874c90d106d241e99894460d1`；小红书脚本固定 fmz200 `2dfe1fa129085015a9abed46b4474d34d4426269`。后两者不跟随 `master/main` 自动改变。上游图标仍是展示资源的浮动地址，不是可执行脚本。

`interval: 86400` 是重新获取同一 URL 的周期，不是自动升级版本。**Stash 不校验清单中的 hash**；release 资产可被上游替换或删除，固定提交资源也可能不可访问。第三方代码可访问解密内容、持久化及脚本 API；这里的静态检查不构成完整安全审计。更新时先下载候选版本，审查脚本、HTTP 匹配和精确域名，核对 hash，再在 PR 中同步配置与清单，不直接换成 `latest` 或浮动脚本。

## 验证范围

仓库离线检查涵盖 YAML 重复键、三个独立覆写的脚本引用、版本固定、精确域名、清单 hash、禁止路由/DNS/CA/TLS 弱化字段以及按官方合并语义叠加后主配置分流不变。生成器不读取此目录，不会把 Stash HTTP 字段带入 FlClash。

尚无 Stash 二进制或 iOS 真机验收，不能声称脚本运行、MitM 握手、通知、当前 App 接口或去广告效果已验证。Mihomo 检查仅验证原有通用配置，**不能验证 Stash 的 HTTP 引擎与脚本**。

参考：[Stash 覆写合并规则](https://stash.wiki/configuration/override)、[MitM 与本机 CA](https://stash.wiki/http-engine/mitm)、[HTTP 脚本](https://stash.wiki/script/rewrite-requests)。
