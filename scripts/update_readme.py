#!/usr/bin/env python3
"""
Awesome-Website-Fingerprinting-Attacks README 自动更新脚本

功能：
1. 从学术 API 搜索网站指纹识别相关论文
2. 自动分类论文
3. 更新 README.md 文件

使用方法：
    python scripts/update_readme.py [--dry-run] [--query QUERY] [--limit LIMIT]

参数：
    --dry-run    预览更新内容，不实际写入文件
    --query      自定义搜索关键词（默认：website fingerprinting）
    --limit      每平台搜索数量（默认：30）
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# README.md 中的分类标题映射
SECTION_MAP = {
    "classic": "## :label:Classic",
    "multi_tab": "## :label:Multi-tab",
    "cross_domain": "## :label:Cross-domain-few-shot",
    "early_stage": "## :label:Early-stage",
    "dataset": "## :open_file_folder:Datasets",
}

# 分类关键词规则
CLASSIFICATION_RULES = {
    "multi_tab": [
        "multi-tab", "multi tab", "multiple tab", "tab-based",
        "parallel browsing", "concurrent tab"
    ],
    "cross_domain": [
        "cross-domain", "cross domain", "few-shot", "few shot", "n shot",
        "n-shot", "zero-shot", "zero shot", "transfer learning",
        "domain adaptation", "domain shift", "traffic drift"
    ],
    "early_stage": [
        "early stage", "early-stage", "early phase", "early-phase",
        "partial trace", "prefix", "initial stage", "first packet"
    ],
    "dataset": [
        "dataset", "benchmark", "data collection", "trace collection",
        "evaluation dataset", "public dataset"
    ],
}


def search_semantic_scholar(query: str, limit: int = 30) -> List[Dict]:
    """搜索 Semantic Scholar API"""
    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={encoded_query}"
        f"&fields=title,authors,year,venue,citationCount,openAccessPdf,externalIds,abstract"
        f"&limit={limit}"
    )

    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        data = json.loads(result.stdout)
        return data.get("data", [])
    except Exception as e:
        print(f"Semantic Scholar 搜索失败: {e}")
        return []


def search_arxiv(query: str, limit: int = 30) -> List[Dict]:
    """搜索 arXiv API"""
    encoded_query = urllib.parse.quote(query)
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=all:{encoded_query}"
        f"&start=0&max_results={limit}"
        f"&sortBy=relevance&sortOrder=descending"
    )

    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        return parse_arxiv_xml(result.stdout)
    except Exception as e:
        print(f"arXiv 搜索失败: {e}")
        return []


def parse_arxiv_xml(xml_content: str) -> List[Dict]:
    """解析 arXiv XML 响应"""
    import xml.etree.ElementTree as ET

    papers = []
    try:
        root = ET.fromstring(xml_content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            paper = {}

            title_elem = entry.find("atom:title", ns)
            paper["title"] = title_elem.text.strip() if title_elem is not None else ""

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text)
            paper["authors"] = [{"name": a} for a in authors]

            published = entry.find("atom:published", ns)
            if published is not None:
                paper["year"] = int(published.text[:4])

            summary = entry.find("atom:summary", ns)
            paper["abstract"] = summary.text if summary is not None else ""

            # 获取 arXiv ID
            id_elem = entry.find("atom:id", ns)
            if id_elem is not None:
                arxiv_id = id_elem.text.split("/")[-1]
                paper["externalIds"] = {"ArXiv": arxiv_id}
                paper["openAccessPdf"] = {"url": f"https://arxiv.org/pdf/{arxiv_id}"}

            paper["venue"] = "arXiv"
            paper["citationCount"] = 0  # arXiv API 不返回引用数

            papers.append(paper)
    except Exception as e:
        print(f"解析 arXiv XML 失败: {e}")

    return papers


def classify_paper(paper: Dict) -> List[str]:
    """根据标题和摘要分类论文"""
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    text = f"{title} {abstract}"

    categories = []

    # 检查每个分类的关键词
    for category, keywords in CLASSIFICATION_RULES.items():
        if any(kw in text for kw in keywords):
            categories.append(category)

    # 如果没有匹配到特定分类，默认归为 classic
    if not categories:
        categories.append("classic")

    return categories


def format_paper_entry(paper: Dict) -> str:
    """格式化单篇论文为 Markdown 条目"""
    title = paper.get("title", "")
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    venue = paper.get("venue", "")
    citation_count = paper.get("citationCount", 0)

    # 格式化作者
    if authors:
        first_author = authors[0].get("name", "Unknown")
        author_str = f"{first_author.split()[-1]} et al."
    else:
        author_str = "Unknown"

    # 获取 PDF 链接
    pdf_url = ""
    external_ids = paper.get("externalIds", {})
    arxiv_id = external_ids.get("ArXiv", "")

    if arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    elif paper.get("openAccessPdf"):
        pdf_url = paper.get("openAccessPdf", {}).get("url", "")

    # 构建条目
    entry = f"- **{title}** - [{author_str}] - [{venue} {year}]"

    if pdf_url:
        entry += f" - [[PDF]]({pdf_url})"

    # 添加引用数（如果有）
    if citation_count and citation_count > 0:
        entry += f" [Cited: {citation_count}]"

    entry += "\n"

    return entry


def get_paper_id(paper: Dict) -> str:
    """生成论文唯一标识用于去重"""
    external_ids = paper.get("externalIds", {})

    # 优先使用 DOI
    if "DOI" in external_ids:
        return external_ids["DOI"]

    # 其次使用 arXiv ID
    if "ArXiv" in external_ids:
        return f"arxiv:{external_ids['ArXiv']}"

    # 最后使用标题+年份
    return f"{paper.get('title', '')}:{paper.get('year', '')}"


def deduplicate_papers(papers: List[Dict]) -> List[Dict]:
    """去重"""
    seen = set()
    unique = []

    for paper in papers:
        paper_id = get_paper_id(paper)
        if paper_id not in seen:
            seen.add(paper_id)
            unique.append(paper)

    return unique


def load_existing_papers(readme_path: str) -> Set[str]:
    """从现有 README.md 中提取已存在的论文标识"""
    existing = set()

    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 尝试匹配 arXiv ID
        arxiv_pattern = r"arxiv\.org/pdf/([\d.]+)"
        existing.update(re.findall(arxiv_pattern, content))

        # 尝试匹配 DOI
        doi_pattern = r"doi\.org/([\S]+)"
        existing.update(re.findall(doi_pattern, content))

    except FileNotFoundError:
        pass

    return existing


def update_readme(readme_path: str, papers_by_category: Dict[str, List[Dict]], dry_run: bool = False):
    """更新 README.md 文件"""
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"错误：找不到 {readme_path}")
        return

    # 记录更新统计
    stats = {cat: 0 for cat in SECTION_MAP.keys()}

    for category, section_title in SECTION_MAP.items():
        if category not in papers_by_category:
            continue

        papers = papers_by_category[category]
        if not papers:
            continue

        # 按年份降序排序
        papers.sort(key=lambda x: x.get("year", 0), reverse=True)

        # 构建新条目
        new_entries = []
        for paper in papers:
            entry = format_paper_entry(paper)
            new_entries.append(entry)
            stats[category] += 1

        # 在对应章节插入
        section_pattern = f"({re.escape(section_title)}.*?)(?=\n## |\Z)"
        match = re.search(section_pattern, content, re.DOTALL)

        if match:
            section_content = match.group(1)
            # 在章节标题后插入新条目
            new_section = section_content.rstrip() + "\n" + "".join(new_entries)
            content = content[:match.start()] + new_section + content[match.end():]

    if dry_run:
        print("\n=== 预览更新内容 ===")
        print(f"\n将更新以下分类：")
        for cat, count in stats.items():
            if count > 0:
                print(f"  - {SECTION_MAP[cat]}: +{count} 篇")
        print("\n（这是预览模式，未实际写入文件）")
    else:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("\n=== 更新完成 ===")
        total = sum(stats.values())
        print(f"共新增 {total} 篇论文：")
        for cat, count in stats.items():
            if count > 0:
                print(f"  - {SECTION_MAP[cat]}: +{count} 篇")


def main():
    parser = argparse.ArgumentParser(description="更新 Awesome-WF README.md")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--query", default="website fingerprinting", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=30, help="每平台搜索数量")
    args = parser.parse_args()

    readme_path = "README.md"

    print(f"开始搜索: {args.query}")
    print(f"每平台限制: {args.limit} 篇")

    # 加载已存在的论文
    existing = load_existing_papers(readme_path)
    print(f"现有论文数: {len(existing)}")

    # 多平台搜索
    all_papers = []

    print("\n搜索 Semantic Scholar...")
    ss_papers = search_semantic_scholar(args.query, args.limit)
    all_papers.extend(ss_papers)
    print(f"  找到 {len(ss_papers)} 篇")

    print("\n搜索 arXiv...")
    arxiv_papers = search_arxiv(args.query, args.limit)
    all_papers.extend(arxiv_papers)
    print(f"  找到 {len(arxiv_papers)} 篇")

    # 去重
    all_papers = deduplicate_papers(all_papers)
    print(f"\n去重后: {len(all_papers)} 篇")

    # 过滤已存在的
    new_papers = [p for p in all_papers if get_paper_id(p) not in existing]
    print(f"新论文: {len(new_papers)} 篇")

    if not new_papers:
        print("\n没有新论文需要添加。")
        return

    # 分类
    papers_by_category = {cat: [] for cat in SECTION_MAP.keys()}

    for paper in new_papers:
        categories = classify_paper(paper)
        for cat in categories:
            if cat in papers_by_category:
                papers_by_category[cat].append(paper)

    # 更新 README
    update_readme(readme_path, papers_by_category, args.dry_run)

    print(f"\n更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
