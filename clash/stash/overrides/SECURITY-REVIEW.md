# Stash 脚本静态隐私与安全审查（2026-11-05）

本报告针对 `sources.json` 的五个唯一脚本字节，不代表未来上游版本。全部五个运行时脚本及内联依赖已固定在本仓库；四个原样保存，微信只前置分发许可声明，其余字节与原固定版本一致。所有 provider 均引用本仓库固定 commit，无外部脚本例外。固定版本阻止上游静默替换代码，不消除已有行为风险。本 PR 保留功能和默认设置，没有自动删功能、安装 CA 或调整设备。

## 审查方法、边界与依赖图

核对五个文件与上一版清单的 SHA-256 和大小；阅读入口、分支、网络请求、通知/重定向、存储与日志、解析器及可执行加载点。对 B 站以固定源码和 lockfile 重建并比较真实 release 字节，模块证据见 [build-evidence.json](../scripts/build-evidence.json)。静态结果区分当前 Stash 路径、显式可选路径、未调用工具和其他运行环境；没有把所有 HTTP 字符串当作请求，也没有把所有 `require` 当作远程下载。

| 入口 | Stash 运行时依赖闭包 | 审查及固定方式 |
| --- | --- | --- |
| B 站 config | 内联设置 JSON；无外部 JS | 固定完整字节；入口只构造 JSON 响应，HEAD 返回空体 |
| B 站 request/response | 内联 util（URL、参数、存储、对象处理、日志/网络适配）、gRPC、pako、protobuf 消息/运行库；request 另含 CryptoJS MD5 | 所有可执行字节已在两个 bundle 内，无外部 JS 下载；包名、精确版本、integrity、许可见 [清单](../scripts/bundled-packages.json) |
| 微信 weixin110 | 内联 he 1.2.0 HTML 实体处理、js-base64 3.7.2 编解码、平台 API 包装 | 版本来自内联代码；原作 GPLv3、墨鱼改动 MIT、he/MIT、js-base64/BSD-3-Clause 分别保留。源码和依赖可编辑源文件已入库；许可头之后的全部原字节由单独上游摘要校验，无 runtime 外部 JS |
| 小红书 xiaohongshu | 内联跨平台 Env；其源版本未标注，以完整脚本 SHA 确定身份 | 原样源文件及 GPLv3 已保存。Stash 使用 `$httpClient` 的存在判断走 `$persistentStore`，没有 Node 包下载 |

B 站构建树中的 `@auraflare/shared`、Hono、fetch-cookie/node-fetch 及它们的 Node 传递依赖不构成设备端的隐式安装链；没有在当前 bundle 中运行或下载它们。CryptoJS 有条件的 `require("crypto")` 是 Node 内建模块探测。小红书 Env 有 `fs/path/got/tough-cookie/iconv-lite` 的 Node 分支，其中非内建包既未锁版本也未提供；当前 Stash 业务没有调用网络方法，也不会走 Node 分支。**这些文件不作为通用 Node 程序受支持，不能据本审查称其 Node 依赖完整。**

单次人工静态审查覆盖五个入口和实际内联代码，审查深度集中在数据流和安全边界；补充验证仅从 SHA 固定的 response bundle 提取已核对的 Console 类，在不提供网络/存储 API 的 Node VM 中以 Stash 标识和合成数据检查日志格式与等级；没有执行 bundle 业务入口。没有进行形式证明、模糊测试、真实账号抓包、iOS/Stash 真机或服务端行为验证，也没有把未观察到恶意上传表述成安全保证。Codex Security 技能的附属流程文件无法通过提供的资源读取，未产出该产品的标准扫描或自动验证报告。

对七个 B 站打包依赖和微信两个可识别 npm 库的精确版本查询 OSV，未返回已知漏洞条目，原始查询/结果见 [advisory-check.json](advisory-check.json)。这是数据库在核对时的结果，不覆盖未发布漏洞、Env 未标版本代码或错误的上游包声明，也不代替代码审查。

## HTTPS、认证数据与信任边界

覆写沿用 README 列明的 25 个精确 MITM 主机。启用后 Stash 可看到这些主机的解密流量；具体脚本在规则命中的请求上可读 URL、headers、响应体，B 站二进制规则还可处理 protobuf/gRPC。URL 和请求头可能带 Cookie、access key/token、签名、设备 ID、用户标识，响应可能含关注、推荐、评论和观看上下文。确切字段取决于 App/API；本次未采集真实用户数据。

`http.mitm` 是解密/触发范围，**不是脚本网络白名单**。脚本信任 Stash 的网络、持久化和通知 API；被替换的脚本原则上能滥用可见数据。仓库固定 commit 和哈希校验减小更新供应链风险，无法限制运行时权限。图标、homepage、BoxJS 打开入口仍是外部资源/网页；它们不是被 script-provider 下载执行的 JS，也未纳入本次设备运行时脚本闭包。不要把另行安装的 BoxJS 或网页脚本视为已审计。

## 已确认行为和建议

### R1：小红书默认将响应和媒体标识写入日志/持久化（中等隐私风险）

证据：[固定脚本](../scripts/sha256/xiaohongshu-318d89bce1117edb26a93b383804e195649ec4674a04efa9e3ddb4ef7f34b498.js)，第 69 行 `打印原body`、126 行 `原body`、151 行 `新body`，356–425 行 note ID、缓存及媒体 URL 日志。首页/详情等命中时存在无日志等级开关的完整 JSON 打印，可能包含账号关联内容、浏览兴趣、评论、带参数的媒体地址；这是默认代码路径，不只是调试日志选项。

`fmz200.xiaohongshu.feed.rsp`、`redBookVideoFeed`、`fmz200.xiaohongshu.comments.rsp`、`fmz200.xiaohongshu.comments.videos.rsp` 保存媒体地址、note/comment/video ID、分辨率等；没有统一过期时间或账号隔离，关闭覆写也不清除。Env 的 `$persistentStore` 分支是本地写入；没有发现业务调用向作者服务器上传这些缓存。实际日志保留/导出策略和存储隔离取决于 Stash。

建议后续单独评估删除完整响应日志、仅保留无标识错误码，为缓存设置有效期和账号隔离；分享日志前先检查并脱敏。清理时只处理这些脚本键，避免删除其他脚本数据。本 PR 为保持功能未改动上游日志和缓存。

### R2：微信回退请求接受页面 URL，可能向非预期主机携带 export key（条件性中等风险）

证据：[原固定源码第 154–195 行](https://github.com/ddgksf2013/Scripts/blob/97b8abea5ff52b5874c90d106d241e99894460d1/weixin110.js#L154)：`type === "block"`，第一次 `decodeBlockedUrl(action.url)` 未得到原链接时，取 `links[0]/btns[0].url` 替换 `newreadtemplate` 为 `redirecthelpcgi`。若 URL 无 exportkey，代码直接追加本地 `UnblockURLinWeChat.wechatExportKey`（有值时），随后 `await get(url)`；已有 exportkey 时也会发请求。`get` 第 245–258 行调用 Stash `$httpClient.get`。

代码未验证协议、目标主机、端口或重定向去向；请求目标来自微信页面而非编译期白名单。能够影响该页面/action 数据的一方可能诱导外发 key，或触发访问其他可达地址。**未证明普通外链作者能控制微信生成的 action URL，也未证明存在实际泄露**；影响依赖页面内容、已保存 key、API 重定向与 Stash 网络策略。不把它报告为已发生的任意远程账号窃取。该请求没有显式复制原始 Cookie/Authorization 头；传输 URL 本身可带 key。禁用快照和强制跳转不关闭这条回退路径。

建议后续独立修复时，将此请求限制到精确 HTTPS 微信端点，校验端口/路径并拒绝跨域重定向，按查询参数方式添加 key；或另行提供不自动联网的实现。本 PR 只增加分发声明并改为本仓库固定引用，保留当前 GET/exportKey 行为，不将取得分发许可或固定版本视为风险已经修复。

### R3：B 站可选空降助手向第三方发送视频标识（低至中等隐私风险，默认关闭）

证据：固定 response bundle 中 `bsbsb.top/api/skipSegments`；对应 [airborne.mjs 第 90–115 行](https://github.com/Biliverse/ADBlock/blob/b0051916843f269d4b377aaf177f0d9e7b12e393/src/function/airborne.mjs#L90)。当 `Settings.DM.Airborne` 开启且走 `DM/DmSegMobile`、可获得请求参数时，GET `https://bsbsb.top/api/skipSegments?videoID=...&cid=...&category=sponsor`，timeout 3 秒，headers 仅显式指定 origin 和 x-ext-version，没有复制 B 站认证头。接收方能看到视频/分集标识、请求时刻与出口 IP；服务端保留策略未知。

数据库默认 `Airborne: false`；bundle 内的 `getStorage`（来自 integrity 核对的 util 2.7.6 包） 的持久化偏好合并可覆盖默认值，不能仅凭默认宣称现有设备关闭。相关 `BiliBili.ADBlock.Airborne.<request id>` 存储用于 request/response 之间暂存 oid/pid/type，消费时尝试删除。当前覆写没有新增该功能所需 request 阶段的 DM 匹配，能否在某台 Stash 上取得参数还取决于请求 API 提供的信息；此处说明可选代码能力，不声称真机必然发出请求。

建议保持该选项关闭，若使用，应接受该第三方可观察观看信息的边界；独立检查已有偏好。固定代码无法对第三方服务的运营方和数据保存策略作保证。

### R4：B 站推荐补位可重发原 URL 和认证头（预期行为/低风险，需知情）

证据：固定 response bundle 的 `@Biliverse.Index.Caches`、`headers:$request.headers`；对应 [Response.mjs 第 202–265 行](https://github.com/Biliverse/ADBlock/blob/b0051916843f269d4b377aaf177f0d9e7b12e393/src/process/Response.mjs#L202)。默认 Feed.AD 开启，补位需要且缓存空时，向原 B 站推荐 API URL 再请求，携带原 headers 和查询参数，随后缓存候选条目；当前命中主机为 app.bilibili.com/app.biliapi.net。缓存中存在个性化推荐和媒体上下文，没有统一 TTL。不是向第三方作者上传，但会产生附加的已认证请求；自动重定向的最终处理由宿主决定，脚本未另做目标校验。

**补位异常日志在默认 WARN 下也会发生。** `fetch(...).then` 内对响应 JSON 解析、条目处理或缓存写入发生异常时，来源第 249–250 行调用 `Console.error(e, response)`；JSON 解析失败是一个明确触发例。util 2.7.6 的 ERROR 门槛为等级 ≥1，WARN 为 2，因此无需打开 INFO/DEBUG。错误对象先被转为字符串，错误消息未脱敏，可能包含引擎生成的响应片段、标识或错误详情；JSC/Stash 实际消息格式和保留策略尚未真机验证。

不能仅凭第二个实参就宣称完整响应头和正文被打印：当前日志类先对每个实参进行模板字符串转换，普通 response 对象变为 `[object Object]`，之后才交给日志输出。新增 [隔离日志测试](../../tests/check_bilibili_logging.js) 从原 bundle 提取实际类，以普通合成响应验证默认 WARN 会输出错误文本和 `[object Object]`，不会结构化输出其中的响应 header/body；若宿主对象有自定义字符串化行为则仍需另查，测试不能替代 Stash 验证。这不是已确认的完整认证头泄露。建议后续单独脱敏异常文本、避免传入完整响应，并核对已产生的日志；只保持 WARN 不能排除此路径。

util 网络适配删除 Host/:authority/Content-Length 等头，其余业务头保留；未关闭 TLS 校验。B 站签名代码用 CryptoJS MD5 和应用协议常量重算请求签名，未发现提交真实用户密钥或挖矿代码。`fetchBilibili` 多主机重试函数在来源中整段注释，不在 bundle 执行路径，不应误报为实际重试。

### R5：通知/响应改写和解析边界（产品/可用性风险）

- 微信通知可显示完整原链接，可能出现在通知中心和锁屏，点击后交给浏览器/支付宝；不会判断外链是否安全。URL 采用 `indexOf("http") == 0` 和 `includes("https://spotify.link")` 等字符串判断，未做严格 scheme/origin 校验。输入可导致意外目标或错误解析；未证明能绕过操作系统处理 scheme 的限制。默认 `useCache=false&forceRedirect=false` 不自动使用 web.archive.org 快照，不强制 302；参数解析 `ture` 拼写缺陷保留，不能据此当作安全控制。
- B 站默认 LogLevel=WARN，INFO/DEBUG URL、设置和部分解析数据日志需相应等级才出现，但 WARN 仍输出 ERROR，补位异常的未脱敏错误文本见 R4；已有持久化配置可改等级。不要把源码里注释的日志算成已执行。广告/跟踪阻断选项并不全部默认开启；固定脚本不是全面反跟踪产品。
- 小红书会删除/重写广告、直播带货、下载限制、水印、画质和部分作者/评论字段，详见功能表；没有发现上传请求，不等于媒体下载会匿名，App 后续仍向响应中的媒体目标联网。脚本缺少部分空值/JSON 错误兜底，递归遍历以及大 JSON/gRPC 解压处理没有统一资源配额；异常或大响应可能导致失败/耗时。尚无可复现的跨边界攻击，按可用性残余风险记录。

## 动态执行与第三方依赖结论

当前五个字节中没有发现远程拉取 JS 后 eval/Function/import 执行的业务路径。小红书内联 Env 的 `getScript` 和 `runScript` **方法定义仍存在**：后者可读取 `@chavy_boxjs_userCfgs.httpapi` 中的 key/地址，以明文 HTTP POST script_text 和 X-Key 到 `/v1/scripting/evaluate`。当前业务没有调用这两个方法，因此不报告成当前数据外发；未来改动若调用它们必须重新审查。B 站 util 里同类工具未进入可执行 bundle。

pako/gRPC/protobuf 的实际用途是解析/重编码响应，CryptoJS 用于 MD5；he/js-base64 只编解码数据，没有在这些库里发现网络上传、外部脚本加载或把解析后数据当 JS 执行的路径。没有发现广告脚本之外的隐蔽遥测、凭证上传、采矿或持续自更新代码。该结论限于核对的具体字节与上述 Stash 路径，不对作者意图、其他环境、依赖所有潜在漏洞或未来版本背书。

## 供应链剩余事项

1. 微信按组合程序 GPLv3 分发，不能将作者对其改动的 MIT 许可误当作对整份原作重新授权。原链接的 master 分支在 `0a70fbe27dfb072dac29423d661ed3c47cf66aab` 提供原脚本、LICENSE 和 README 的 GPLv3 声明；前次仅检查默认 main 分支的缺失结论已纠正。用户提供的授权作为墨鱼本人改动的 MIT 依据，身份/具体版本范围未独立认证，公开文档只记录依据和限制，不公开私人证据内容。MIT/BSD-3-Clause 与 GPL 的兼容性可参考 [GNU 许可说明](https://www.gnu.org/licenses/license-list.en.html)；全部版权、许可及可编辑依赖源文件均保留，详见 [授权复核记录](wechat-permission-review.json)。
2. 五个本仓库运行时文件引用先前快照 commit 的完整 SHA，带 SHA-256 路径；CI 对比本地和该提交中的真实 blob，检查缺失、篡改、配置引用、已知模块加载、声明剥除后的上游字节、可编辑依赖源码/许可证及语法。清单是审查证据，Stash 不强制校验摘要；必须保留快照提交可达性，按 README 使用 merge commit 合并。
3. 更新需要新的源码/包许可核对、闭包审查、字节比较和新快照提交，之后才能换覆写引用。不能只改哈希让测试通过，更不能把 URL 换为 main/latest 或恢复可替换 release 资产。
4. 真机仍需人工核对脚本下载、应用登录/播放、通知、CA/MITM、App API 变化及日志；仓库 CI 和 Mihomo 都不能替代 Stash HTTP 引擎测试。
