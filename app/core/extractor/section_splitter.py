"""简历段落切分器：将简历文本切分为结构化段落"""
import re
from dataclasses import dataclass, field


@dataclass
class ResumeSections:
    """简历结构化段落"""
    raw_text: str = ""

    # 基础信息
    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    expected_position: str = ""

    # 教育信息
    education: list = field(default_factory=list)  # [{school, major, degree, start, end}]

    # 技能
    skills: list = field(default_factory=list)

    # 工作/实习经历
    work_experience: list = field(default_factory=list)  # [{company, position, start, end, description}]

    # 项目经历
    projects: list = field(default_factory=list)  # [{name, role, description}]

    # 其他
    self_intro: str = ""
    honors: list = field(default_factory=list)
    certificates: list = field(default_factory=list)
    languages: list = field(default_factory=list)

    # 全局统计
    total_chars: int = 0
    total_sections: int = 0


class SectionSplitter:
    """简历段落识别与切分"""

    # 段落标题关键词
    SECTION_HEADERS = {
        "education": ["教育背景", "教育经历", "学历", "学习经历", "Education"],
        "skills": ["技能", "专业技能", "技术栈", "掌握技能", "职业技能", "Skills", "技术能力"],
        "work": ["工作经历", "工作经验", "实习经历", "工作背景", "Experience", "Work Experience"],
        "project": ["项目经历", "项目经验", "Projects", "Project Experience", "个人项目"],
        "self_intro": ["自我介绍", "个人评价", "自我评价", "个人简介", "关于我", "Summary", "Profile"],
        "honors": ["荣誉", "奖项", "获奖", "证书", "资格", "Honors", "Awards", "Certificates"],
    }

    def split(self, text: str) -> ResumeSections:
        """将简历全文切分为结构化段落"""
        sections = ResumeSections(raw_text=text)
        sections.total_chars = len(text)

        if not text.strip():
            return sections

        lines = text.split('\n')

        # 逐行分析
        current_section = "header"  # header / education / skills / work / project / other
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测段落标题
            detected_section = self._detect_section(line)
            if detected_section:
                current_section = detected_section
                continue

            # 根据当前段落类型处理
            if current_section == "header":
                self._parse_header(line, sections)
            elif current_section == "education":
                self._parse_education_line(line, sections)
            elif current_section == "skills":
                self._parse_skills_line(line, sections)
            elif current_section == "work":
                self._parse_work_line(line, sections)
            elif current_section == "project":
                self._parse_project_line(line, sections)
            elif current_section == "self_intro":
                sections.self_intro += line + " "
            elif current_section == "honors":
                sections.honors.append(line)

        # 后处理
        sections.self_intro = sections.self_intro.strip()
        sections.total_sections = sum([
            1 if sections.education else 0,
            1 if sections.skills else 0,
            1 if sections.work_experience else 0,
            1 if sections.projects else 0,
            1 if sections.self_intro else 0,
        ])

        return sections

    def _detect_section(self, line: str) -> str:
        """检测是否为段落标题"""
        line_clean = line.strip().rstrip('：:').lower()

        # 匹配已知标题
        for section_type, keywords in self.SECTION_HEADERS.items():
            for kw in keywords:
                if kw.lower() in line_clean:
                    return section_type

        # 启发式：短行 + 关键词
        if len(line) < 20:
            if any(kw in line_clean for kw in ['教育', '学历', 'edu']):
                return "education"
            if any(kw in line_clean for kw in ['技能', 'skill', '技术']):
                return "skills"
            if any(kw in line_clean for kw in ['工作', '实习', '经验', '经历', 'work', 'exp']):
                return "work"
            if any(kw in line_clean for kw in ['项目', 'project']):
                return "project"
            if any(kw in line_clean for kw in ['自我', '个人', '介绍', '评价', 'about', 'summary']):
                return "self_intro"
            if any(kw in line_clean for kw in ['荣誉', '奖项', '获奖', '证书', 'honor', 'award']):
                return "honors"

        return ""

    def _parse_header(self, line: str, sections: ResumeSections):
        """解析简历头部信息"""
        # 姓名（首行2-4个汉字）
        if not sections.name:
            name_match = re.match(r'^[一-龥]{2,4}$', line)
            if name_match:
                sections.name = line
                return

        # 手机
        phone_match = re.search(r'1[3-9]\d{9}', line)
        if phone_match and not sections.phone:
            sections.phone = phone_match.group()

        # 邮箱
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
        if email_match and not sections.email:
            sections.email = email_match.group()

        # 期望职位
        if '期望' in line or '求职' in line or '意向' in line:
            sections.expected_position = line

    def _parse_education_line(self, line: str, sections: ResumeSections):
        """解析教育经历"""
        # 尝试匹配: 学校 | 专业 | 学历 | 时间
        parts = re.split(r'[|｜]', line)
        if len(parts) >= 2:
            edu = {
                "school": parts[0].strip() if len(parts) > 0 else "",
                "major": parts[1].strip() if len(parts) > 1 else "",
                "degree": "",
                "start": "",
                "end": "",
            }
            # 学历
            degree_match = re.search(r'(博士|硕士|本科|专科|大专|学士|Master|Bachelor|PhD)', line)
            if degree_match:
                edu["degree"] = degree_match.group()

            # 时间
            date_match = re.search(r'(\d{4})[年\-./]*\s*[至\-~到]+\s*(\d{4}|至今|现在)', line)
            if date_match:
                edu["start"] = date_match.group(1)
                edu["end"] = date_match.group(2)

            sections.education.append(edu)
        else:
            # 简单追加到最近的教育条目
            sections.education.append({"school": line, "major": "", "degree": ""})

    def _parse_skills_line(self, line: str, sections: ResumeSections):
        """解析技能"""
        # 可能是一行多个技能（逗号/顿号分隔）或每行一个技能
        skills_in_line = re.split(r'[,，、/]', line)
        for skill in skills_in_line:
            skill = skill.strip().rstrip(';；')
            if skill and len(skill) < 50:
                sections.skills.append(skill)

    def _parse_work_line(self, line: str, sections: ResumeSections):
        """解析工作经历"""
        # 检测新的工作条目（公司名开头）
        date_match = re.search(r'(\d{4}[年.\-/]\d{1,2})\s*[至\-~到]\s*(\d{4}[年.\-/]\d{1,2}|至今|现在)', line)
        if date_match or re.match(r'.*(公司|集团|科技|有限).*', line):
            sections.work_experience.append({
                "company": "",
                "position": "",
                "start": "",
                "end": "",
                "description": line,
            })
        elif sections.work_experience:
            sections.work_experience[-1]["description"] += " " + line

    def _parse_project_line(self, line: str, sections: ResumeSections):
        """解析项目经历"""
        sections.projects.append({"name": "", "role": "", "description": line})
