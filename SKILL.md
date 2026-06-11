---
name: awesome-wf-updater
description: |
  自动搜索"网站指纹识别(Website Fingerprinting)"领域的最新学术论文，并将搜索结果按分类结构更新到 README.md 中。
  当用户要求"更新文献"、"搜索论文"、"添加新论文"或类似请求时触发此 Skill。
metadata:
  version: "1.0.0"
---

# Awesome-Website-Fingerprinting-Attacks Updater Skill

## 目标

自动搜索网站指纹识别(Website Fingerprinting) 领域的学术论文，筛选高质量论文，并将它们按分类更新到项目的 README.md 文件中。

## 前置检查

在开始之前，检查以下依赖是否可用：

- **curl**: 必需，用于调用学术 API
- **Python 3.6+**: 可选，如果使用自动更新脚本

## 搜索策略

### 查询扩展

执行搜索时，使用以下关键词组合覆盖不同命名习惯：

| 查询组合 | 说明 |
|---------|------|
| `website fingerprinting` | 标准术语 |
| `traffic analysis attack` | 相关术语 |
| `Tor fingerprinting` | Tor 场景 |
| `WF attack` | 缩写形式 |
| `deep learning website fingerprinting` | 深度学习方向 |
| `defense website fingerprinting` | 防御方向 |

### 平台选择

| 需求 | 首选平台 | 访问方式 |
|------|---------|---------|
| 广泛搜索 | **Semantic Scholar** | REST API |
| 预印本 | **arXiv** | REST API |
| 引用数 | **Semantic Scholar** | REST API |
| 代码可用性 | **Papers with Code** | REST API |

### API 调用模板

**Semantic Scholar 搜索：**
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=website+fingerprinting&fields=title,authors,year,venue,citationCount,openAccessPdf,externalIds,abstract&limit=30"
```

**arXiv 搜索：**
```bash
curl -s "http://export.arxiv.org/api/query?search_query=all:website+fingerprinting&start=0&max_results=30&sortBy=relevance&sortOrder=descending"
```

## 文献分类规则

根据论文标题和摘要，将论文分类到 README.md 的对应章节：

| 分类 | README 章节 | 关键词判断规则 |
|------|------------|---------------|
| **classic** | ## :label:Classic | 经典/基础的网站指纹识别方法，包括深度学习 WF 攻击 |
| **multi_tab** | ## :label:Multi-tab | 包含 `multi-tab`、`multiple tab`、`tab` 等多标签场景 |
| **cross_domain** | ## :label:Cross-domain-few-shot | 包含 `cross-domain`、`few-shot`、`transfer`、`domain adaptation`、`N shot` 等 |
| **early_stage** | ## :label:Early-stage | 包含 `early stage`、`early-phase`、`partial trace`、`prefix` 等早期识别 |
| **defense** | （归入 Classic 或对应分类）| 标题/摘要包含 `defense`、`countermeasure`、`mitigation`、`protection` 等 |
| **dataset** | ## :open_file_folder:Datasets | 标题/摘要包含 `dataset`、`benchmark`、`data collection` 等 |

## 更新流程

### 1. 执行搜索（两遍策略）

**第一遍（轻量扫描）：**
- 使用多个查询组合搜索
- 获取轻量摘要：标题、作者、年份、venue、引用数、PDF 状态
- 按引用数 + 年份排序，筛选出核心论文

**第二遍（深入获取）：**
- 对筛选出的核心论文，获取完整元数据（摘要、PDF 链接、代码链接）

### 2. 分类处理

- 读取每篇论文的标题和摘要
- 根据"文献分类规则"判断所属分类
- 允许多个分类（如一篇论文可能同时属于 Deep Learning 和 Defenses）

### 3. 格式化输出

每篇论文使用以下格式：

```markdown
- **{Title}** - [{FirstAuthor} et al.] - [{Venue} {Year}] - [[PDF]]({pdf_url}) [[Code]]({code_url})
  > {一句话贡献概述}
```

### 4. 更新 README.md

- 读取当前 README.md
- 在每个分类章节下，将新论文按年份降序排列插入
- 避免重复：通过 DOI 或 arXiv ID 去重
- 保留已有论文，只添加新论文

## 去重规则

1. **DOI 相同** → 同一篇论文，跳过
2. **arXiv ID 相同** → 同一篇论文，跳过
3. **标题 + 年份相同** → 同一篇论文，跳过

## 排序规则

每个分类内的论文按以下优先级排序：

1. **年份**：新论文优先（降序）
2. **引用数**：同一年份，高引用优先
3. **Venue 等级**：CS 会议参考 CCF 分级

## 注意事项

- 只添加真正相关的论文，宁缺毋滥
- 优先选择有开放获取 PDF 的论文
- 如果有代码链接，一并提供
- 更新后告知用户：新增多少篇、更新到哪个分类
- 如果 API 返回 429（速率限制），等待 15 秒后再试

## 示例使用

用户说：
- "更新文献"
- "搜索最新的网站指纹识别论文"
- 