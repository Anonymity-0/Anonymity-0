# 拔草花园动画

主页使用 `garden-output` 分支中的 `chiikawa-light.svg` 和 `chiikawa-dark.svg`，根据浏览器的配色偏好切换。画布透明，角色沿相邻格子移动，在有贡献的日期格子上停下拔草。每个有贡献的格子在完成拔草时清空。

GitHub Actions 每天获取最近一年的真实贡献记录，按日期位置和贡献等级重绘。计划时间为北京时间 08:17，实际执行时间由 GitHub 调度决定，也可以在 Actions 页面手动运行“更新贡献草地”。生成结果发布在单独的动画分支。

实现参考 [Platane/snk](https://github.com/Platane/snk) 的数据读取、网格映射和逐格清除方式。角色路线采用各自区域内的最近格子优先策略。生成脚本为 `scripts/render_garden.py`，只依赖 Python 标准库。

角色参考 [Chiikawa Dots Pets](https://github.com/heelee912/chiikawa-dots-pets) 的乌萨奇和小八形象，通过 imagegen 生成新的拔草姿势，再编排成动画。

本动画为非官方同人创作。Chiikawa 及相关角色归 Nagano 和相应权利人所有。
