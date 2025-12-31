#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别模块
支持自动识别数字和字母组合的验证码
"""

import io
import re
import os
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


@dataclass
class CaptchaResult:
    """验证码识别结果"""
    success: bool
    text: str
    confidence: float
    method: str
    message: str


class CaptchaRecognizer:
    """验证码识别器"""
    
    # 验证码字符白名单（数字+大小写字母）
    CHAR_WHITELIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    
    # 易混淆字符映射（用于后处理校正）
    CONFUSION_MAP = {
        'O': '0', 'o': '0',  # O和0
        'I': '1', 'l': '1', '|': '1',  # I、l和1
        'Z': '2',  # Z和2
        'S': '5',  # S和5
        'B': '8',  # B和8
        'G': '6',  # G和6
        'Q': '9',  # Q和9
    }
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        初始化验证码识别器
        
        Args:
            tesseract_path: Tesseract OCR可执行文件路径（可选）
        """
        self.tesseract_path = tesseract_path
        self._check_dependencies()
        
        if tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # 初始化 ddddocr
        self.ddddocr = None
        if DDDDOCR_AVAILABLE:
            try:
                self.ddddocr = ddddocr.DdddOcr(show_ad=False)
            except Exception as e:
                print(f"警告: ddddocr初始化失败: {e}")
        
        # 初始化 easyocr
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                print("[*] 验证码识别器: 使用 easyocr")
            except Exception as e:
                print(f"警告: easyocr初始化失败: {e}")
    
    def _check_dependencies(self):
        """检查依赖"""
        self.pil_available = PIL_AVAILABLE
        self.numpy_available = NUMPY_AVAILABLE
        self.cv2_available = CV2_AVAILABLE
        self.tesseract_available = TESSERACT_AVAILABLE
        
        if not self.pil_available:
            print("警告: PIL未安装，验证码处理功能将受限")
        if not self.tesseract_available:
            print("警告: pytesseract未安装，OCR功能将不可用")
    
    def recognize(self, image_data: bytes, preprocess: bool = True) -> CaptchaResult:
        """
        识别验证码
        
        Args:
            image_data: 图片二进制数据
            preprocess: 是否预处理图片
            
        Returns:
            CaptchaResult
        """
        if not self.pil_available:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="none",
                message="PIL库未安装，无法处理图片"
            )
        
        try:
            # 加载图片
            image = Image.open(io.BytesIO(image_data))
            
            # 尝试多种识别方法
            results = []
            
            # 方法0: 使用 ddddocr 识别（优先级最高）
            if self.ddddocr:
                result = self._ddddocr_recognize(image_data)
                if result.success:
                    results.append(result)
            
            # 方法1: 使用 easyocr 识别
            if self.easyocr_reader:
                result = self._easyocr_recognize(image_data)
                if result.success:
                    results.append(result)
            
            # 方法2: 直接OCR
            if self.tesseract_available:
                result = self._ocr_recognize(image, preprocess=False)
                results.append(result)
            
            # 方法3: 预处理后OCR
            if self.tesseract_available and preprocess:
                preprocessed = self._preprocess_image(image)
                result = self._ocr_recognize(preprocessed, preprocess=True)
                results.append(result)
            
            # 方法4: 增强预处理后OCR
            if self.tesseract_available and preprocess and self.cv2_available:
                enhanced = self._enhanced_preprocess(image)
                if enhanced:
                    result = self._ocr_recognize(enhanced, preprocess=True)
                    results.append(result)
            
            # 选择最佳结果
            best_result = self._select_best_result(results)
            return best_result
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="error",
                message=f"识别失败: {str(e)}"
            )
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        预处理图片（基础版）
        
        Args:
            image: PIL图片对象
            
        Returns:
            预处理后的图片
        """
        # 转换为灰度图
        if image.mode != 'L':
            image = image.convert('L')
        
        # 调整大小（放大有助于识别）
        width, height = image.size
        if width < 200:
            scale = 200 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 增强锐度
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # 二值化处理
        threshold = 128
        image = image.point(lambda p: 255 if p > threshold else 0)
        
        # 去噪（使用中值滤波）
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def _enhanced_preprocess(self, image: Image.Image) -> Optional[Image.Image]:
        """
        增强预处理（使用OpenCV）
        
        Args:
            image: PIL图片对象
            
        Returns:
            预处理后的图片或None
        """
        if not self.cv2_available or not self.numpy_available:
            return None
        
        try:
            # PIL转OpenCV格式
            img_array = np.array(image)
            
            # 转灰度
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 放大图片
            height, width = gray.shape[:2]
            if width < 200:
                scale = 200 / width
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            
            # 高斯模糊去噪
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 自适应阈值二值化
            binary = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # 形态学操作（去除噪点）
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # 转回PIL格式
            result = Image.fromarray(binary)
            return result
            
        except Exception as e:
            return None
    
    def _easyocr_recognize(self, image_data: bytes) -> CaptchaResult:
        """
        使用 easyocr 识别验证码
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            CaptchaResult
        """
        if not self.easyocr_reader:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="easyocr",
                message="easyocr未初始化"
            )
        
        try:
            # 使用 easyocr 识别
            result = self.easyocr_reader.readtext(image_data, detail=0)
            
            if result:
                # 合并识别结果
                combined_text = ''.join(result)
                # 清理结果
                cleaned_text = self._postprocess_text(combined_text)
                
                return CaptchaResult(
                    success=bool(cleaned_text),
                    text=cleaned_text,
                    confidence=0.90,  # easyocr 通常有很高的准确率
                    method="easyocr",
                    message="识别成功" if cleaned_text else "未识别到有效字符"
                )
            else:
                return CaptchaResult(
                    success=False,
                    text="",
                    confidence=0.0,
                    method="easyocr",
                    message="未识别到有效字符"
                )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="easyocr",
                message=f"easyocr错误: {str(e)}"
            )
    
    def _ddddocr_recognize(self, image_data: bytes) -> CaptchaResult:
        """
        使用 ddddocr 识别验证码
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            CaptchaResult
        """
        if not self.ddddocr:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="ddddocr",
                message="ddddocr未初始化"
            )
        
        try:
            # 使用 ddddocr 识别
            result_text = self.ddddocr.classification(image_data)
            
            # 清理结果
            cleaned_text = self._postprocess_text(result_text)
            
            return CaptchaResult(
                success=bool(cleaned_text),
                text=cleaned_text,
                confidence=0.95,  # ddddocr 通常有很高的准确率
                method="ddddocr",
                message="识别成功" if cleaned_text else "未识别到有效字符"
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="ddddocr",
                message=f"ddddocr错误: {str(e)}"
            )
    
    def _ocr_recognize(self, image: Image.Image, preprocess: bool) -> CaptchaResult:
        """
        OCR识别
        
        Args:
            image: PIL图片对象
            preprocess: 是否已预处理
            
        Returns:
            CaptchaResult
        """
        if not self.tesseract_available:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="ocr",
                message="Tesseract未安装"
            )
        
        try:
            # 配置OCR参数
            config = f'--oem 3 --psm 8 -c tessedit_char_whitelist={self.CHAR_WHITELIST}'
            
            # 获取详细数据（包含置信度）
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            # 提取文本和置信度
            texts = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                conf = int(data['conf'][i])
                if text.strip() and conf > 0:
                    texts.append(text.strip())
                    confidences.append(conf)
            
            if texts:
                combined_text = ''.join(texts)
                avg_confidence = sum(confidences) / len(confidences) / 100.0
            else:
                # 备用方法：直接识别
                combined_text = pytesseract.image_to_string(image, config=config).strip()
                avg_confidence = 0.5 if combined_text else 0.0
            
            # 后处理
            cleaned_text = self._postprocess_text(combined_text)
            
            method = "ocr_preprocessed" if preprocess else "ocr_direct"
            
            return CaptchaResult(
                success=bool(cleaned_text),
                text=cleaned_text,
                confidence=avg_confidence,
                method=method,
                message="识别成功" if cleaned_text else "未识别到有效字符"
            )
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="ocr",
                message=f"OCR错误: {str(e)}"
            )
    
    def _postprocess_text(self, text: str) -> str:
        """
        后处理识别结果
        
        Args:
            text: 原始识别文本
            
        Returns:
            清理后的文本
        """
        # 移除空白字符
        text = text.replace(' ', '').replace('\n', '').replace('\t', '')
        
        # 只保留白名单字符
        cleaned = ''.join(c for c in text if c in self.CHAR_WHITELIST)
        
        return cleaned
    
    def _correct_confusion(self, text: str, prefer_digits: bool = True) -> str:
        """
        校正易混淆字符
        
        Args:
            text: 原始文本
            prefer_digits: 是否偏好数字（验证码通常是纯数字或数字居多）
            
        Returns:
            校正后的文本
        """
        if not prefer_digits:
            return text
        
        result = []
        for char in text:
            if char in self.CONFUSION_MAP:
                result.append(self.CONFUSION_MAP[char])
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _select_best_result(self, results: list) -> CaptchaResult:
        """
        选择最佳识别结果
        
        Args:
            results: 多个识别结果
            
        Returns:
            最佳结果
        """
        if not results:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="none",
                message="无可用识别结果"
            )
        
        # 按置信度和文本长度排序
        valid_results = [r for r in results if r.success and r.text]
        
        if not valid_results:
            # 返回第一个结果（即使失败）
            return results[0]
        
        # 选择置信度最高且文本长度合理的结果（验证码通常4-6个字符）
        def score(result: CaptchaResult) -> float:
            length_score = 1.0 if 4 <= len(result.text) <= 6 else 0.5
            return result.confidence * length_score
        
        best = max(valid_results, key=score)
        return best
    
    def recognize_from_url(self, url: str, session=None) -> CaptchaResult:
        """
        从URL识别验证码
        
        Args:
            url: 验证码图片URL
            session: requests会话对象（可选）
            
        Returns:
            CaptchaResult
        """
        import requests
        
        try:
            if session:
                response = session.get(url, timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            response.raise_for_status()
            return self.recognize(response.content)
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="url",
                message=f"获取验证码图片失败: {str(e)}"
            )
    
    def recognize_from_file(self, filepath: str) -> CaptchaResult:
        """
        从文件识别验证码
        
        Args:
            filepath: 图片文件路径
            
        Returns:
            CaptchaResult
        """
        try:
            with open(filepath, 'rb') as f:
                image_data = f.read()
            return self.recognize(image_data)
            
        except Exception as e:
            return CaptchaResult(
                success=False,
                text="",
                confidence=0.0,
                method="file",
                message=f"读取文件失败: {str(e)}"
            )


def check_tesseract_installed() -> Tuple[bool, str]:
    """
    检查Tesseract是否已安装
    
    Returns:
        (是否安装, 版本信息或错误消息)
    """
    if not TESSERACT_AVAILABLE:
        return False, "pytesseract库未安装，请运行: pip install pytesseract"
    
    try:
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract版本: {version}"
    except Exception as e:
        return False, f"Tesseract未安装或不在PATH中: {str(e)}\n请从 https://github.com/UB-Mannheim/tesseract/wiki 下载安装"


def quick_recognize(image_data: bytes) -> str:
    """
    快速识别验证码
    
    Args:
        image_data: 图片二进制数据
        
    Returns:
        识别的验证码文本（失败返回空字符串）
    """
    recognizer = CaptchaRecognizer()
    result = recognizer.recognize(image_data)
    return result.text if result.success else ""


if __name__ == "__main__":
    # 测试代码
    installed, msg = check_tesseract_installed()
    print(f"Tesseract状态: {msg}")
    
    if installed:
        # 测试识别（需要测试图片）
        import sys
        if len(sys.argv) > 1:
            filepath = sys.argv[1]
            recognizer = CaptchaRecognizer()
            result = recognizer.recognize_from_file(filepath)
            print(f"识别结果: {result.text}")
            print(f"置信度: {result.confidence:.2%}")
            print(f"方法: {result.method}")
            print(f"消息: {result.message}")