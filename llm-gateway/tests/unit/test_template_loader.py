"""模板加载器测试"""

import pytest

from app.infrastructure.template_loader import TemplateLoader
from app.core.exceptions import TemplateNotFoundException


class TestTemplateLoader:
    """模板加载器测试"""

    def test_render_template(self):
        """测试模板渲染"""
        loader = TemplateLoader()
        result = loader.render(
            "v1:chat_default",
            {"role": "Python助手", "language": "中文", "user_input": "你好"},
        )
        assert "Python助手" in result
        assert "中文" in result
        assert "你好" in result

    def test_render_code_review(self):
        """测试代码审查模板渲染"""
        loader = TemplateLoader()
        result = loader.render(
            "v1:code_review",
            {"language": "Go", "code": "func main() {}"},
        )
        assert "Go" in result
        assert "func main()" in result

    def test_template_not_found(self):
        """测试不存在的模板"""
        loader = TemplateLoader()
        with pytest.raises(TemplateNotFoundException):
            loader.render("v1:nonexistent", {})

    def test_list_templates(self):
        """测试列出所有模板"""
        loader = TemplateLoader()
        templates = loader.list_templates()
        assert "v1:chat_default" in templates
        assert "v1:code_review" in templates
        assert "v2:chat_default" in templates
        assert "v2:code_review" in templates

    def test_v2_template_enhanced(self):
        """测试 v2 增强版模板"""
        loader = TemplateLoader()
        result = loader.render(
            "v2:chat_default",
            {
                "role": "代码助手",
                "language": "中文",
                "output_format": "markdown",
                "user_input": "解释闭包",
            },
        )
        assert "代码助手" in result
        assert "Markdown" in result
        assert "解释闭包" in result