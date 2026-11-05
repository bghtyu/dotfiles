# Stash 脚本快照

`sha256/` 内是从原覆写下载、核对旧清单后固定的脚本；四个原样保存，微信仅前置分发/许可声明，移除声明后与原文件逐字节一致。文件名包含实际分发文件的完整 SHA-256。不编辑已发布文件，升级时新增文件。`snapshot.json` 记录来源、大小、摘要、运行时脚本依赖及跨平台代码中的静态 `require`。

这些文件不统一适用本仓库根目录的 Apache-2.0：

- Biliverse ADBlock v0.7.5：Apache-2.0。作者 ClydeTime、VirgilClyne、app2smile、RuCu6、Maasea；对应源提交 `b0051916843f269d4b377aaf177f0d9e7b12e393`。三个 bundle 已含全部运行时 JS；许可和包的原始 `package.json` 保存在 `licenses/`，七个实际打入 bundle 的包见 `bundled-packages.json`。保留 pako 的内联声明，同时补齐 protobuf-ts 的两项 BSD 声明。`@biliverse/protobuf` npm 包声明 Apache-2.0，但未附许可正文，这里随附相同 Apache-2.0 文本；其 GitHub 源仓库在核对时不可访问。
- fmz200 小红书：原样可编辑 JavaScript 源文件（含内联 Env 工具），适用来源仓库固定提交的 GPLv3，完整文本为 `licenses/fmz200-GPL-3.0.txt`。未改动、未压缩源文件，保留作者和注释；这是一项独立程序的集合分发，不将其改授 Apache-2.0。来源 README 另提醒不要在中国大陆平台传播项目内容；本次分发目标为 GitHub。
- 微信 ddgksf2013/weixin110.js：按组合程序 GPLv3 分发，保留 zZPiglet 原作、ddgksf2013 修改者署名；不将整份文件标成 MIT。原链接明确指向的 `master` 分支在提交 `0a70fbe27dfb072dac29423d661ed3c47cf66aab` 同时提供原脚本、README 的 GPLv3 声明和 LICENSE；前次仅检查默认 main 分支而误判原文件不可用，现已纠正。用户提供的作者 MIT 许可作为墨鱼本人改动的授权依据，身份/具体版本范围未独立认证，公开记录只保留这一依据和限制，不发布私聊截图、原文或联系信息。he 1.2.0（Mathias Bynens，MIT）、js-base64 3.7.2（Dan Kogai，BSD-3-Clause）许可均单独保留。完整许可见 `licenses/wechat-*`，原作及两库的可编辑源文件见 `sources/wechat/`，来源与摘要见 `wechat-components.json`，授权复核见 [记录](../overrides/wechat-permission-review.json)。本仓库只于 2026-11-05 增加许可头，不改业务逻辑；原作及内嵌库不能因后续 MIT 许可而丢失自身条款。

`build-evidence.json` 记录 Biliverse 构建核对及实际渲染模块清单。使用固定源提交、原 lockfile 的版本和 integrity，通过 npm 公共镜像获取两个原 GitHub Packages 项目（tarball integrity 相同），以 `npm ci --ignore-scripts` 安装工具，执行原 Rollup 构建；配置 bundle 字节完全一致，request/response 去掉首行构建时间后字节完全一致。配置生成输入从已下载 config bundle 中以 JSON 解析提取；因此证明的是 JS 打包内容对应源代码和锁定依赖，未独立复现 arguments-builder 的配置生成过程。没有执行这些 Stash 业务脚本，也没有运行包的安装脚本。`rendered_modules` 含 Rollup/CommonJS 合成模块标识；它们不是运行时远程依赖。build-only 工具及没有渲染进 bundle 的 Node/Worker 依赖不需要设备另行下载。

覆写应在**后续提交**中引用包含本目录的先前完整提交 SHA，不能让提交引用自身。保留那个快照提交的可达性（使用 merge commit 合并本 PR，避免 squash/rebase 丢掉快照祖先；如必须 squash，应先单独合入资产快照，再重新生成引用）。分支和 PR 本身已包含快照祖先；下载无需等覆写合入 main。Stash 不执行清单中的哈希验证，仓库测试和固定 commit 负责防止无意变更；客户端仍信任 GitHub HTTPS、Stash 和配置更新来源。

离线检查：`python clash/scripts/check_stash_scripts.py`。更新/审查流程见 [覆写说明](../overrides/README.md)，风险见 [静态审查](../overrides/SECURITY-REVIEW.md)。
