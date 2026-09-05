# 编辑

README 正文有两个 `YOUR WORDS` 注释位置，直接在注释下写 Markdown 即可。空白块可通过移除第二个 `<picture>` 替换成自己的内容。主页只保留用户名和 `repos ↗` 链接。

`assets/entry-{light,dark}.svg` 是顶部，`assets/space-{light,dark}.svg` 是留白区域。修改图内文字时同步两种主题，保留 viewBox；新增正文优先写 Markdown，避免移动端缩小后难读。

两个主题都保持有色暗底，light 版加强外缘，dark 版降低外缘对比；正文和链接由 GitHub 的主题样式负责。无脚本、外部字体、统计服务、动画或构建依赖。SVG 内的细线是装饰，不是可点击控件。

README 采用分支相对资源路径。无需替换成 main 的绝对地址；GitHub 会按当前分支解析。合并前个人主页仍不会显示此 README。
