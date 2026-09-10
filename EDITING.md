# 编辑主页

正文默认留空，保留原稿的裂痕、斜光、五个项目画面、ashes 和 trace 区域。

## 填写文字

在 `scripts/build_assets.py` 顶部的 `HERO_LINES`、`NOW_LINES`、`ASHES_LINES` 中填写自己的短句，例如 `HERO_LINES = ("第一行", "第二行")`，然后运行 `python3 scripts/build_assets.py`。空元组 `()` 表示不显示文字。脚本会同时更新桌面与移动 SVG；它只依赖 Python 标准库。更改主图文字后，还需按下文重新生成动图，让动态与静态版本显示同一份文字。正文也可以直接写在 README 的 `EDITABLE` 注释位置，但那会使用 GitHub 的页面样式，不在暗色画布内。

图中的 `identity`、`hero-words`、`now-label`、`now-words`、`works-label`、`ashes-label`、`ashes-words` 和 `trace-label` 是可定位的文字组。优先编辑生成器，直接改成品 SVG 的内容会在下次生成时覆盖。

## 项目与链接

README 使用真正的 HTML 链接包裹项目小图；四个公开仓库可点击。`fish-meditate` 在制作时没有公开仓库目标，保留第一张小图但不提供失效链接。未来有地址后，在它的 `<img>` 外加 `<a href="实际地址">…</a>` 即可。

项目图片显示宽度为 160px，窄屏自然换行。`alt` 使用完整项目名称，部分图内名称为了可读性缩短。GitHub 和 repositories 链接位于底部；没有编造 Email 或微博地址。

## 视觉资源

`assets/materials/` 是从用户批准原稿的非文字区域量化描摹得到的原生 SVG 路径，保留其纹理与构图形态；它们不是嵌入 PNG，也不是新的随机粒子图。原图 SHA-256 和区域记录在 `assets/materials/manifest.json`。修改构图时编辑生成器的素材坐标、缩放和文字。

所有展示资源均使用仓库内相对路径，无网页脚本、外部字体、统计或外部服务。明暗模式都使用自带暗底的画布。移动版本放大必要标签，README 的 `<picture>` 在视口不大于 1024px 时选择它们。GitHub 自身的页面底色、Markdown 区块间距、图片焦点边框不由 README 控制。

## 局部慢动

主图仅有裂痕亮部和斜光变化，水面卡片只有反光轻微晃动；文字、版式、其他四张卡片和页脚保持静止。动图是从同一份 SVG 生成的 12 秒、10 帧/秒 GIF，固定调色板，不逐帧添加噪点。原生 SVG 素材始终保留，未嵌入位图。

主图在原运动区域内保留 4 个源图像素宽的静止边缘，再向内用 4 个像素逐渐恢复亮度变化，以减少缩放时亮部越过边界的影响。运动区域范围不变；这项处理不代表浏览器截图与账户自动播放设置已完成验收。

`scripts/build_motion.py` 生成 `hero-motion.gif`、`hero-mobile-motion.gif`、`work-fish-motion.gif`，同时更新 `assets/motion-manifest.json` 的源文件哈希、尺寸和循环信息。运行环境需要 Python 的 Pillow、NumPy，以及 Node.js 的 Sharp；制作时使用 Pillow 12.3.0、NumPy 2.3.5、Node 24.19.0、Sharp 0.35.4，无需视频生成服务。

在具备这些库的环境中运行 `python3 scripts/build_motion.py`。Node 不在搜索路径时，用 `--node /实际路径/node` 指定；Sharp 不在默认模块位置时，用环境变量 `PROFILE_SHARP_MODULE=/实际路径/node_modules/sharp` 指定。脚本按自身位置找到仓库，不依赖制作电脑的固定目录。

系统开启“减少动态”时，README 优先选择对应的静态 SVG。GitHub 也提供 Settings → Accessibility → Motion → Autoplay animated images 设置；本 README 对账户设置的实际响应仍需网页验收确认。请保留静态 source 在移动动图 source 之前的顺序，以及五张卡片共享的同一个 `<p>`，避免回退错误和换行变化。

生成后运行 `python3 scripts/verify_motion.py --rebuild`，检查整段动图解码、局部变化范围、12 秒循环、资源哈希、体积与可重复生成。动图修改后还需在真实 GitHub 检查自动播放、静态回退和卡片布局；本地帧检查不能替代网页验收。

`python3 scripts/verify_assets.py` 单独检查 SVG 结构、README 路径与静态资源可重复生成。只有 feature 分支上的变更通过 PR 合并后，公开个人主页才会显示本 README。
