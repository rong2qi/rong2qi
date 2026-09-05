# 编辑主页

正文默认留空，保留原稿的裂痕、斜光、五个项目画面、ashes 和 trace 区域。

## 填写文字

在 `scripts/build_assets.py` 顶部的 `HERO_LINES`、`NOW_LINES`、`ASHES_LINES` 中填写自己的短句，例如 `HERO_LINES = ("第一行", "第二行")`，然后运行 `python3 scripts/build_assets.py`。空元组 `()` 表示不显示文字。脚本会同时更新桌面与移动 SVG；它只依赖 Python 标准库。正文也可以直接写在 README 的 `EDITABLE` 注释位置，但那会使用 GitHub 的页面样式，不在暗色画布内。

图中的 `identity`、`hero-words`、`now-label`、`now-words`、`works-label`、`ashes-label`、`ashes-words` 和 `trace-label` 是可定位的文字组。优先编辑生成器，直接改成品 SVG 的内容会在下次生成时覆盖。

## 项目与链接

README 使用真正的 HTML 链接包裹项目小图；四个公开仓库可点击。`fish-meditate` 在制作时没有公开仓库目标，保留第一张小图但不提供失效链接。未来有地址后，在它的 `<img>` 外加 `<a href="实际地址">…</a>` 即可。

项目图片显示宽度为 160px，窄屏自然换行。`alt` 使用完整项目名称，部分图内名称为了可读性缩短。GitHub 和 repositories 链接位于底部；没有编造 Email 或微博地址。

## 视觉资源

`assets/materials/` 是从用户批准原稿的非文字区域量化描摹得到的原生 SVG 路径，保留其纹理与构图形态；它们不是嵌入 PNG，也不是新的随机粒子图。原图 SHA-256 和区域记录在 `assets/materials/manifest.json`。修改构图时编辑生成器的素材坐标、缩放和文字。

所有资源均为仓库内相对路径，无脚本、动画、外部字体、统计或网络依赖。明暗模式都使用自带暗底的画布。`*-mobile.svg` 放大必要标签，README 的 `<picture>` 在视口不大于 1024px 时选择它们。GitHub 自身的页面底色、Markdown 区块间距、图片焦点边框不由 README 控制。

生成后运行 `python3 scripts/verify_assets.py` 检查资源结构、相对路径与可重复生成。只有 feature 分支上的变更通过 PR 合并后，公开个人主页才会显示本 README。
