"""GameAssistant wrappers — 连接 Web 平台与核心 ML/PC 模块的桥梁层。"""
from app.wrappers.adb_wrapper import ADBWrapper
from app.wrappers.detector_wrapper import DetectorWrapper
from app.wrappers.template_wrapper import TemplateWrapper

__all__ = ["ADBWrapper", "DetectorWrapper", "TemplateWrapper"]
