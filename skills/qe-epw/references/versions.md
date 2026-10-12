# 版本与资料更新

核对日期：2026-10-12。

| 范围 | 状态 |
|---|---|
| QE 7.3.1 / EPW 5.8.1 | 常规输入生成与离线关键字检查；快照来自 QEF 官方发布版 |
| EPW 6.1 当前网页 | 已参考其输入索引和教程；不等同于旧版离线校验依据 |
| 其他版本/高级物性 | 先核对该发布版官方文档、示例及真实 namelist |

实际 EPW 版本应从已有日志确认；目录叫 qe/7.3.1 并不说明所有 EPW 构建相同。

已有可确认的差异：5.8.1 用 eps_acustic、wfpt；当前 6.1 页用 eps_acoustic、lwfpt。5.8.1 源码的 kmaps 是内部变量、不在 inputepw namelist 中，而 6.1 文档将其列为输入。不要给旧版输入补上新版变量。新文档上的物性功能也不证明旧版实现已经支持。

离线 registry 保存的是参数标识符和源文件 SHA256，没有缓存或复制整本手册。其键名检查不是完整的类型、单位、编译选项或算法兼容性证明。

在相同版本、相同已覆盖阶段重复准备输入时，优先使用本地参考和工具。更换版本、遇到未知变量、更新物性算法或出现与参考不符的报错时，才定向查匹配来源，并更新快照及行为验证。不要把所有联网查询变成每次任务的强制步骤。

优先来源：
- EPW 输入：https://docs.epw-code.org/Inputs/Inputs.html
- EPW 教程：https://docs.epw-code.org/Tutorials.html
- QE PW 输入：https://www.quantum-espresso.org/Doc/INPUT_PW.html
- QE PH 输入：https://www.quantum-espresso.org/Doc/INPUT_PH.html
- 官方版本源码：https://github.com/QEF/q-e/tree/qe-7.3.1

生成工具仅支持缓存的版本组合；其他版本可以手工按正确文档编写，再建立新的输入快照，不能把旧版检查通过冒充新版验证。
