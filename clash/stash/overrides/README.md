# Stash 可选覆写

三个现成 Stash 覆写的独立适配文件，只用于 Stash。主配置 `clash/stash.yaml` 和 FlClash 配置、代理、DNS、分组、分流及生成器均不改变；导入主配置不会自动加载这些文件。无 YouTube 覆写。

| 文件 | 来源 | 功能与边界 |
| --- | --- | --- |
| [bilibili.stoverride](bilibili.stoverride) | [Biliverse ADBlock v0.7.5](https://github.com/Biliverse/ADBlock/releases/download/v0.7.5/BiliBili.ADBlock.stoverride) | 开屏、推荐、搜索、动态、播放页等广告及界面净化；保留上游默认偏好和 BoxJS 配置入口，通常无需 BoxJS 即可使用。已移除非广告用途的 `Teenagers/ModeStatus` 青少年模式弹窗处理，省略上游空 `argument` 字段（官方定义类型为字符串）。 |
| [wx110.stoverride](wx110.stoverride) | [qsoyq wx110](https://github.com/qsoyq/shell/blob/29d9e686c29a5b22f4ca6239c73dc035ad808c2f/config/stash/override/ad/wx110.stoverride) | 墨鱼 weixin110 脚本，匹配微信外链提示页，提取链接并发通知，用户点击到浏览器打开；不保证所有链接均可打开，也不判定链接安全。仅支持该脚本识别的页面结构，Stash 通知权限需开启。 |
| [rednote.stoverride](rednote.stoverride) | [HotKids RedNote](https://github.com/HotKids/Rules/blob/e8970451207e555d7fc8005ca9df9b3bb5821564/Surge/Module/Stash/RedNote.stoverride) / fmz200 | 开屏、搜索、首页等广告与界面净化；还包含图片/视频/评论区去水印和下载处理、信息流直播/带货/商品过滤、保存及画质相关设置、评论 `red_id` 字段改名为 `fmz200`、媒体下载作者字段设置为 `@fmz200`，并持久化媒体链接，并非只去广告。 |

## 导入与独立开关

1. 使用已经填入自己订阅的 Stash 主配置。在 Stash 的覆写管理中，分别从文件导入上述三个 `.stoverride`，或使用以下本仓库地址（主分支会在合并后更新；审阅本 PR 时下载分支中的覆写并本地导入，脚本引用在分支推送后即可访问）。它们是覆写，不是完整代理配置。

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

[sources.json](sources.json) 保留原覆写和脚本来源、大小、SHA-256 与调整记录。五个唯一运行时脚本均已固定到 [scripts/](../scripts/README.md)，包含内联依赖及许可证/声明；覆写 URL 全部指向本仓库快照提交 `cb223267964cef6154921a57596379ab2e422569` 下的内容寻址文件。B 站三个 bundle 和小红书脚本逐字节保持原样，微信仅新增 616 字节的分发许可头，移除后与原始文件逐字节一致。没有修改脚本业务功能或默认偏好。B 站构建与原 release 除时间行外一致，证据和依赖版本已入库。

微信以组合程序 GPLv3 分发：原作 zZPiglet 的明确 GPLv3 依据在原链接 `master` 分支已核实；用户提供的墨鱼 MIT 授权用于其本人改动，保留 he/MIT、js-base64/BSD-3-Clause 的声明及可编辑源文件。原始与实际分发文件的摘要、许可来源及用户提供证据的认证限制分别记录于清单和 [授权复核](wechat-permission-review.json)。授权私聊的截图、原文和联系信息未发布。

完整 [静态安全与隐私审查](SECURITY-REVIEW.md) 包含各脚本和内联依赖的数据流、网络目标/触发、认证数据、可选功能、日志、持久化、动态执行及未验证项。已确认小红书完整响应/媒体日志和缓存、微信回退请求主机校验不足、B 站可选第三方空降服务、认证请求补位，以及默认 WARN 仍输出的补位异常错误文本等行为。此处固定版本不能消除这些行为。微信授权依据的复核记录见 [wechat-permission-review.json](wechat-permission-review.json)。

`interval: 86400` 只是重新获取同一固定 URL 的周期。Stash 不校验清单 hash；客户端仍信任 GitHub HTTPS、Stash 与覆写来源。图标仍是外部展示资源，homepage/BoxJS 是用户打开的网页入口，不是本次运行时 JS。**请以 merge commit 合并本 PR**，保留被引用的快照祖先；需要 squash/rebase 时先单独合入脚本快照，再重新引用其最终提交，避免丢掉固定提交的可达性。

更新步骤：

1. 在临时目录下载候选版本及完整运行时依赖图，记录完整源提交、字节、大小与摘要；先核对主文件和内联依赖许可，不复制许可不清或禁止再分发的内容。不要运行下载的业务脚本。
2. 审查 HTTP/MITM 范围和所有网络/跳转/存储/日志/动态加载路径，更新风险与构建证据。原 bundle 已包含的代码无需在设备再加载；出现新的二次脚本依赖时必须继续解析和固定，不能只改 hash 放行。
3. 新增内容寻址脚本文件、许可证与快照/依赖清单，先单独提交；不改写或删除仍被使用的旧资产。随后另一个提交更新覆写、`script_snapshot_commit` 和 sources 中的 URL/摘要，引用前一个提交的完整 SHA，避免自指。
4. 执行 `python clash/scripts/check_stash_scripts.py`、`python -m unittest discover -s clash/tests -v` 及 CI。推送后再次从实际 raw URL 下载比较摘要；若访问失败不发布该覆写。检查微信许可声明、依赖源文件和剥除声明后的上游摘要；不允许新增外部脚本例外或静默回退。
5. 在 PR 中审阅代码和报告；用 merge commit 保留快照历史，再由用户按需进行 Stash/iOS 验收和启停。回滚可关闭对应覆写，或恢复前一份已审阅的配置；已产生的日志和缓存需要另行处理。

## 验证范围

仓库离线检查涵盖 YAML 重复键、三个独立覆写的脚本引用、完整 commit/内容寻址、本地及 commit blob 字节、缺失/篡改/未固定依赖失败路径、JS 语法、精确域名、清单 hash、禁止路由/DNS/CA/TLS 弱化字段以及按官方合并语义叠加后主配置分流不变。生成器不读取此目录，不会把 Stash HTTP 字段带入 FlClash。另有仅提取固定 bundle 日志类的隔离合成测试，验证 WARN/ERROR 和响应对象字符串化边界；不执行 Stash 业务入口。

尚无 Stash 二进制或 iOS 真机验收，不能声称脚本运行、MitM 握手、通知、当前 App 接口或去广告效果已验证。Mihomo 检查仅验证原有通用配置，**不能验证 Stash 的 HTTP 引擎与脚本**。

参考：[Stash 覆写合并规则](https://stash.wiki/configuration/override)、[MitM 与本机 CA](https://stash.wiki/http-engine/mitm)、[HTTP 脚本](https://stash.wiki/script/rewrite-requests)。
