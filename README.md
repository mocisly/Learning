# 钢琴学习与练习曲集

每首曲子独立保存原谱、分段配置和学习笔记；公共模板只负责整本书的排版。完整原谱不添加字母音名，字母音名及升降记号只出现在独立练习谱中。

## 目录

```text
Learning/
├─ book.json                     # 书名、作者、曲目顺序与启用状态
├─ main.tex                      # 整本书入口，不直接写某首曲子的内容
├─ build.py                      # 统一命令入口
├─ run_make.bat                  # Windows 双击构建，支持传入命令参数
├─ tex/
│  ├─ preamble.tex               # A4、字体、页眉页脚、共用命令
│  ├─ note-name-guide.tex        # 字母音名的共用说明
│  └─ frontmatter/               # 封面、前言、引言、封底
├─ assets/images/                # 手工维护的图片素材
├─ lilypond/note-names.ily        # 共用音名标注逻辑
├─ pieces/
│  └─ chopin-waltz-e-minor/
│     ├─ piece.json              # 作品资料、分段范围、调号、提取参数
│     ├─ source/score.ly         # 唯一需要手工维护的原谱
│     └─ study/
│        ├─ overview.tex         # 本曲学习顺序与说明
│        └─ segments/01.tex…     # 各段练习笔记
├─ scripts/
│  ├─ project.py                 # 读取配置、校验曲目和小节范围
│  ├─ practice.py                # 生成、排版分段谱；成功后写缓存标记
│  ├─ book.py                    # 生成书内目录、编译与导出 PDF
│  └─ build.py                   # 构建、新增曲目、检查等命令
├─ templates/piece/              # 新曲目脚手架
├─ tests/                        # 多曲目构建流程的回归检查
├─ build/                        # 自动生成，可重新构建
│  ├─ generated/<构建目标>/      # LaTeX 书籍资料和曲目目录
│  ├─ scores/<曲目 ID>/          # 分段 .ly、PDF、PNG、日志与缓存标记
│  ├─ latex/<构建目标>/          # LaTeX 中间文件与逐轮编译日志
│  └─ cache/                     # 字体、原谱排版、图片转换等缓存
├─ output/
│  ├─ book.pdf                   # 整本曲集
│  └─ pieces/<曲目 ID>.pdf       # 单曲导出
```

只编辑 `book.json`、`pieces/`、`tex/`、`assets/`、`lilypond/` 和构建代码；不要手工修改 `build/` 中的生成文件。`build/` 和 `output/` 已加入 Git 忽略规则。

## 构建

需要 Python 3.10+、带中文字体支持的 LuaLaTeX（TeX Live）及 LilyPond 2.26；`python`、`lualatex`、`lilypond` 必须在 PATH 上。当前模板使用 Windows 字体；换系统时调整 `main.tex` 的 `fontset`。脚本本身只使用 Python 标准库。

在项目根目录执行：

```powershell
python build.py                         # 整本曲集 → output/book.pdf
python build.py --piece chopin-waltz-e-minor
                                        # 单曲 → output/pieces/chopin-waltz-e-minor.pdf
python build.py list                     # 曲目顺序及启用状态
python build.py check                    # 校验并生成分段源码，不调用排版软件
python build.py check --piece chopin-waltz-e-minor
python build.py --jobs 2                 # 限制并行 LilyPond 数量
python build.py --force                  # 强制重新排版所选曲目的分段谱
python -B -m unittest discover -s tests  # 回归检查，不要求启动排版软件
```

也可双击 `run_make.bat`。每次构建先处理分段谱，再编译两轮 LaTeX，以更新目录和页码。整本与单曲使用不同的生成目录、日志和 PDF 文件，不会互相覆盖；同一目标不要同时启动两次构建。曲目的分段谱在两个目标之间共用成功缓存。

LaTeX 失败时查看 `build/latex/<目标>/pass-1.log` 或 `pass-2.log`；分段排版失败时查看 `build/scores/<曲目 ID>/part-XX.log`。失败的构建不会覆盖 `output/` 内上一次成功的 PDF。

## 加入下一首曲子

```powershell
python build.py new chopin-next-piece --title "肖邦：下一首练习曲" --composer "Frédéric Chopin"
```

这会创建 `pieces/chopin-next-piece/` 并登记到 `book.json`，初始状态为 `enabled: false`，以免把空白占位谱加入曲集。

1. 将真实的 LilyPond 乐谱放入该曲目的 `source/score.ly`，填写 `piece.json` 的作品资料。
2. 先保持 `segments: []`，即可用 `python build.py --piece chopin-next-piece` 构建完整谱。
3. 准备分段时，在 `piece.json` 中填写 `extraction` 和 `segments`；范围、标题、起始调号只在这里维护。可参照现有圆舞曲的配置。
4. 在 `study/segments/XX.tex` 中记录对应练习方法；使用 `\CurrentSegmentRange` 引用配置中的范围，使用 `\SegmentScore` 插入当前段谱图，不写死图片路径。
5. 执行 `python build.py check --piece chopin-next-piece`，确认配置和边界可用后，将 `book.json` 中的 `enabled` 改为 `true`。数组顺序就是书内曲目顺序。

书内每首作品为一章，下面依次是“完整乐谱”和“分段练习”；练习各段为小节目录。新增曲目不需要修改 `main.tex` 或构建脚本。

## 分段源码约定

完整谱可以单独使用；自动分段采用 `bar-comments` 提取配置，适用于已有圆舞曲这样的 LilyPond 导出结构，不会自动识别任意来源乐谱的曲式或小节边界。

- 主声部每小节结尾有 `% 1`、`% 2` 等编号注释，分段边界必须能找到对应注释。
- `voices` 配置主声部、伴奏与两个补充声部变量；`score_variable` 指定总谱变量，默认 `pianoMusic`。`staves` 指定上下谱表名称，默认 `up`、`down`。
- `pickup_duration`、`first_full_bar`、`bar_duration` 分别指定弱起时值、首个完整小节编号、每完整小节时值；时值为全音符的分数。例如本曲为 `1/4`、`2`、`3/4`。
- 每段设置 `first_bar`、`last_bar`、`key`、`lesson`，各段须连续覆盖到 `extraction.last_bar`。反复结尾按源码中的印刷编号计数。
- 分段副本保留原谱的音符、指法、力度与反复信息，单独重新换行；首行调号按该段配置补齐。修改原谱、提取参数或音名辅助文件后，相关分段会重新生成。
- 当前提取方式使用 LilyPond 的 `skipTypesetting` 和 `showFirstLength`。某些截断处 LilyPond 2.26 会报告排版警告；实际输出仍需目视核对跨段连线、延音与反复结尾。谱图在 LaTeX 中按图框裁切。

书名、描述、作者与年份统一在 `book.json` 修改；封面、PDF 属性和书内目录由同一配置生成。项目仅保留当前音乐学习版本，旧模板备份和无关编程示例已删除。`build/` 在构建时自动创建，可以随时清空；最终 PDF 保存在 `output/`。
