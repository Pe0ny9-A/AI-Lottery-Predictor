import sys
import requests
import http.client
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QComboBox, QLineEdit, QCompleter, QFrame, QGroupBox, QProgressBar,
    QSplitter, QSizePolicy, QSpacerItem, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

YUNWU_API_KEY = "your_api_key_here"
YUNWU_API_URL = "https://yunwu.ai/v1/chat/completions"

# 真实开奖数据API配置
LOTTERY_API_CONFIG = {
    "双色球": {
        "api_url": "https://datachart.500.com/ssq/history/newinc/history.php",
        "params": {},
        "type": "500"
    },
    "大乐透": {
        "api_url": "https://datachart.500.com/dlt/history/newinc/history.php", 
        "params": {},
        "type": "500"
    }
}

# 备用API配置（如果主API失败）
BACKUP_LOTTERY_API_CONFIG = {
    "双色球": {
        "api_url": "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice",
        "params": {
            "name": "ssq",
            "pageNo": 1,
            "pageSize": 30,
            "systemType": "PC"
        },
        "type": "cwl"
    },
    "大乐透": {
        "api_url": "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice",
        "params": {
            "name": "dlt",
            "pageNo": 1,
            "pageSize": 30,
            "systemType": "PC"
        },
        "type": "cwl"
    }
}

class SearchableComboBox(QComboBox):
    """可搜索的下拉框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.completer().setFilterMode(Qt.MatchContains)
        self.completer().setCompletionMode(QCompleter.PopupCompletion)
        
        # 设置样式
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 8px 12px;
                background: white;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #2980b9;
            }
            QComboBox:focus {
                border-color: #e74c3c;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #3498db;
                margin-right: 5px;
            }
        """)
        
    def addItems(self, items):
        super().addItems(items)
        # 更新completer的模型
        self.completer().setModel(self.model())

class StyledButton(QPushButton):
    """样式化按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #1f5f8b);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f5f8b, stop:1 #154360);
            }
            QPushButton:disabled {
                background: #bdc3c7;
                color: #7f8c8d;
            }
        """)

class SecondaryButton(QPushButton):
    """二次预测按钮样式"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                min-height: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #a93226, stop:1 #922b21);
            }
            QPushButton:disabled {
                background: #bdc3c7;
                color: #7f8c8d;
            }
        """)

class PredictorWindow(QWidget):
    def __init__(self):
        try:
            print("正在初始化PredictorWindow...")
            super().__init__()
            
            self.setWindowTitle("🎯 AI 彩票预测助手")
            self.setWindowIcon(self.create_icon())
            self.available_models = []
            self.is_predicting = False
            self.is_secondary_predicting = False
            self.first_prediction_result = None
            self.first_prediction_numbers = []
            
            # 设置窗口属性
            self.setMinimumSize(1200, 800)
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #ecf0f1, stop:1 #bdc3c7);
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                }
            """)
            
            print("正在初始化UI...")
            self.init_ui()
            print("正在加载模型...")
            self.load_models()
            print("PredictorWindow初始化完成")
            
        except Exception as e:
            print(f"PredictorWindow初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def create_icon(self):
        """创建应用图标"""
        # 创建一个简单的图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(52, 152, 219))  # 蓝色背景
        return QIcon(pixmap)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题区域
        title_label = QLabel("🎯 AI 彩票预测助手")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background: rgba(255, 255, 255, 0.8);
                border-radius: 15px;
                border: 2px solid #3498db;
            }
        """)
        main_layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 上半部分：控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 下半部分：结果显示（使用标签页）
        result_panel = self.create_result_panel()
        splitter.addWidget(result_panel)
        
        # 设置分割器比例 - 控制面板更小，结果显示更大
        splitter.setSizes([150, 600])
        main_layout.addWidget(splitter)

        # 状态栏
        self.status_bar = QLabel("就绪 - 请选择AI模型和彩票类型开始预测")
        self.status_bar.setStyleSheet("""
            QLabel {
                background: rgba(52, 152, 219, 0.1);
                border: 1px solid #3498db;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
                color: #2c3e50;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        
        # 初始化完成后加载历史数据
        self.load_history_data()

    def create_control_panel(self):
        """创建控制面板"""
        panel = QGroupBox("⚙️ 预测设置")
        panel.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background: rgba(255, 255, 255, 0.9);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)  # 减少间距，让界面更紧凑

        # 模型选择
        model_group = QGroupBox("🤖 AI 模型选择")
        model_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                background: rgba(255, 255, 255, 0.7);
            }
        """)
        model_layout = QVBoxLayout()
        
        model_label = QLabel("请选择AI模型（可搜索）：")
        model_label.setStyleSheet("font-size: 11px; color: #2c3e50; margin-bottom: 3px;")
        model_layout.addWidget(model_label)
        
        self.model_combo = SearchableComboBox()
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 彩票类型选择
        lottery_group = QGroupBox("🎲 彩票类型")
        lottery_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                background: rgba(255, 255, 255, 0.7);
            }
        """)
        lottery_layout = QVBoxLayout()
        
        lottery_label = QLabel("请选择彩票类型：")
        lottery_label.setStyleSheet("font-size: 11px; color: #2c3e50; margin-bottom: 3px;")
        lottery_layout.addWidget(lottery_label)
        
        self.lottery_type_combo = QComboBox()
        self.lottery_type_combo.addItems(["双色球", "大乐透"])
        self.lottery_type_combo.currentTextChanged.connect(self.on_lottery_type_changed)
        self.lottery_type_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e74c3c;
                border-radius: 6px;
                padding: 6px 10px;
                background: white;
                font-size: 12px;
                min-height: 16px;
            }
            QComboBox:hover {
                border-color: #c0392b;
            }
            QComboBox:focus {
                border-color: #e74c3c;
            }
        """)
        lottery_layout.addWidget(self.lottery_type_combo)
        lottery_group.setLayout(lottery_layout)
        layout.addWidget(lottery_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 第一次预测按钮
        self.predict_button = StyledButton("🚀 开始预测")
        self.predict_button.clicked.connect(self.do_predict)
        button_layout.addWidget(self.predict_button)
        
        # 二次预测按钮
        self.secondary_predict_button = SecondaryButton("🎯 二次预测")
        self.secondary_predict_button.clicked.connect(self.do_secondary_predict)
        self.secondary_predict_button.setEnabled(False)  # 初始禁用
        button_layout.addWidget(self.secondary_predict_button)
        
        layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                background: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        panel.setLayout(layout)
        return panel

    def create_result_panel(self):
        """创建结果面板"""
        panel = QGroupBox("📊 预测结果")
        panel.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #27ae60;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background: rgba(255, 255, 255, 0.9);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                border: 2px solid #bdc3c7;
                padding: 10px 20px;
                margin-right: 3px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
                border-color: #3498db;
            }
            QTabBar::tab:hover {
                background: #2980b9;
                color: white;
            }
        """)
        
        # 第一次预测结果标签页
        self.first_result_tab = QWidget()
        first_result_layout = QVBoxLayout()
        
        self.first_result_output = QTextEdit()
        self.first_result_output.setReadOnly(True)
        self.first_result_output.setStyleSheet("""
            QTextEdit {
                border: 2px solid #27ae60;
                border-radius: 8px;
                padding: 15px;
                background: white;
                font-size: 15px;
                line-height: 1.8;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
            }
            QTextEdit:focus {
                border-color: #2ecc71;
            }
        """)
        self.first_result_output.setPlaceholderText("第一次预测结果将在这里显示...\n\n💡 提示：\n1. 选择AI模型和彩票类型\n2. 点击'开始预测'按钮\n3. 等待AI分析完成\n4. 完成第一次预测后可进行二次预测")
        
        first_result_layout.addWidget(self.first_result_output)
        self.first_result_tab.setLayout(first_result_layout)
        
        # 二次预测结果标签页
        self.secondary_result_tab = QWidget()
        secondary_result_layout = QVBoxLayout()
        
        self.secondary_result_output = QTextEdit()
        self.secondary_result_output.setReadOnly(True)
        self.secondary_result_output.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 15px;
                background: white;
                font-size: 15px;
                line-height: 1.8;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
            }
            QTextEdit:focus {
                border-color: #c0392b;
            }
        """)
        self.secondary_result_output.setPlaceholderText("二次预测结果将在这里显示...\n\n💡 提示：\n1. 先完成第一次预测\n2. 点击'二次预测'按钮\n3. AI将分析第一次预测结果\n4. 给出1-2组最高中奖率的号码")
        
        secondary_result_layout.addWidget(self.secondary_result_output)
        self.secondary_result_tab.setLayout(secondary_result_layout)
        
        # 历史数据标签页
        self.history_tab = QWidget()
        history_layout = QVBoxLayout()
        
        # 历史数据标题和控制区域
        history_header = QHBoxLayout()
        
        history_title = QLabel("📈 历史开奖数据")
        history_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background: rgba(52, 152, 219, 0.1);
                border-radius: 8px;
                border: 1px solid #3498db;
            }
        """)
        history_header.addWidget(history_title)
        
        # 期数选择
        period_label = QLabel("期数选择：")
        period_label.setStyleSheet("font-size: 12px; color: #2c3e50; font-weight: bold;")
        history_header.addWidget(period_label)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["最近50期", "最近100期", "最近200期", "最近500期", "最近1000期"])
        self.period_combo.setCurrentText("最近100期")
        self.period_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #3498db;
                border-radius: 6px;
                padding: 6px 10px;
                background: white;
                font-size: 12px;
                min-height: 16px;
            }
            QComboBox:hover {
                border-color: #2980b9;
            }
        """)
        history_header.addWidget(self.period_combo)
        
        # 刷新按钮
        self.refresh_history_button = StyledButton("🔄 刷新数据")
        self.refresh_history_button.clicked.connect(self.refresh_history_data)
        self.refresh_history_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                min-height: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #229954, stop:1 #1e8449);
            }
            QPushButton:disabled {
                background: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        history_header.addWidget(self.refresh_history_button)
        
        # 强制刷新按钮
        self.force_refresh_button = StyledButton("🔄 强制更新")
        self.force_refresh_button.clicked.connect(self.force_refresh_history_data)
        self.force_refresh_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                min-height: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
            }
            QPushButton:disabled {
                background: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        history_header.addWidget(self.force_refresh_button)
        
        # 缓存状态标签
        self.cache_status_label = QLabel("缓存状态: 未加载")
        self.cache_status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
                padding: 4px 8px;
                background: rgba(189, 195, 199, 0.2);
                border-radius: 4px;
                border: 1px solid #bdc3c7;
            }
        """)
        history_header.addWidget(self.cache_status_label)
        
        # 添加弹性空间
        history_header.addStretch()
        
        history_layout.addLayout(history_header)
        
        # 历史数据表格
        self.history_table = QTextEdit()
        self.history_table.setReadOnly(True)
        
        # 历史数据加载进度条
        self.history_progress = QProgressBar()
        self.history_progress.setVisible(False)
        self.history_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 6px;
                text-align: center;
                background: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 4px;
            }
        """)
        self.history_table.setStyleSheet("""
            QTextEdit {
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 15px;
                background: white;
                font-size: 14px;
                line-height: 1.8;
                font-family: 'Microsoft YaHei', 'Consolas', monospace;
            }
        """)
        self.history_table.setPlaceholderText("历史开奖数据将在这里显示...\n\n💡 提示：\n1. 选择彩票类型和期数\n2. 点击'刷新数据'从500网获取真实历史数据\n3. 点击'强制更新'忽略缓存获取最新数据\n4. 数据来源：500网 (datachart.500.com)\n5. 备用数据源：中国福利彩票官网 (cwl.gov.cn)\n6. 数据会自动缓存，提高加载速度\n7. 缓存有效期为24小时\n8. 如果API请求失败，将显示详细错误信息")
        
        # 连接信号
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        
        # 初始化历史数据存储
        self.init_history_storage()
        
        history_layout.addWidget(self.history_progress)
        history_layout.addWidget(self.history_table)
        self.history_tab.setLayout(history_layout)

        # 添加标签页
        self.tab_widget.addTab(self.first_result_tab, "🎲 第一次预测")
        self.tab_widget.addTab(self.secondary_result_tab, "🎯 二次预测")
        self.tab_widget.addTab(self.history_tab, "📈 历史数据")
        
        layout.addWidget(self.tab_widget)
        panel.setLayout(layout)
        return panel

    def load_history_data(self):
        """加载历史开奖数据"""
        lottery_type = self.lottery_type_combo.currentText()
        period = self.period_combo.currentText()
        
        # 显示加载提示
        loading_text = f"正在加载{lottery_type}{period}历史数据...\n\n请稍候，正在从中国福利彩票官网获取真实开奖数据..."
        self.history_table.setPlainText(loading_text)
        
        # 异步加载历史数据
        self.refresh_history_data()

    def init_history_storage(self):
        """初始化历史数据存储"""
        import os
        import json
        from datetime import datetime
        
        # 创建数据存储目录
        self.data_dir = os.path.join(os.path.dirname(__file__), "history_data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 历史数据缓存文件
        self.history_cache_file = os.path.join(self.data_dir, "history_cache.json")
        self.history_cache = {}
        
        # 加载现有缓存
        if os.path.exists(self.history_cache_file):
            try:
                with open(self.history_cache_file, 'r', encoding='utf-8') as f:
                    self.history_cache = json.load(f)
            except Exception as e:
                print(f"加载历史数据缓存失败: {e}")
                self.history_cache = {}

    def save_history_data(self, lottery_type, period, data):
        """保存历史数据到本地"""
        import json
        from datetime import datetime
        
        try:
            # 创建缓存键
            cache_key = f"{lottery_type}_{period}"
            
            # 保存数据和时间戳
            self.history_cache[cache_key] = {
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "lottery_type": lottery_type,
                "period": period
            }
            
            # 写入文件
            with open(self.history_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_cache, f, ensure_ascii=False, indent=2)
                
            print(f"历史数据已保存: {cache_key}")
            
        except Exception as e:
            print(f"保存历史数据失败: {e}")

    def get_cached_history_data(self, lottery_type, period):
        """获取缓存的历史数据"""
        import json
        from datetime import datetime, timedelta
        
        cache_key = f"{lottery_type}_{period}"
        
        if cache_key in self.history_cache:
            cached_data = self.history_cache[cache_key]
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            
            # 检查缓存是否过期（24小时）
            if datetime.now() - timestamp < timedelta(hours=24):
                print(f"使用缓存的历史数据: {cache_key}")
                self.update_cache_status("已缓存", "green")
                return cached_data["data"]
            else:
                print(f"历史数据缓存已过期: {cache_key}")
                self.update_cache_status("已过期", "orange")
                return None
        
        self.update_cache_status("无缓存", "red")
        return None

    def update_cache_status(self, status, color):
        """更新缓存状态显示"""
        color_map = {
            "green": "#27ae60",
            "orange": "#f39c12", 
            "red": "#e74c3c"
        }
        
        self.cache_status_label.setText(f"缓存状态: {status}")
        self.cache_status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {color_map.get(color, "#7f8c8d")};
                padding: 4px 8px;
                background: rgba(189, 195, 199, 0.2);
                border-radius: 4px;
                border: 1px solid {color_map.get(color, "#bdc3c7")};
            }}
        """)

    def fetch_real_lottery_data(self, lottery_type, period):
        """从真实API获取彩票历史数据"""
        try:
            if lottery_type not in LOTTERY_API_CONFIG:
                return f"不支持的彩票类型: {lottery_type}"
            
            config = LOTTERY_API_CONFIG[lottery_type]
            
            # 根据期数设置pageSize
            period_map = {
                "最近50期": 50,
                "最近100期": 100,
                "最近200期": 200,
                "最近500期": 500,
                "最近1000期": 1000
            }
            page_size = period_map.get(period, 100)
            
            # 使用统一的请求头
            headers = self.get_headers()
            
            # 根据API类型选择不同的处理方法
            if config.get("type") == "500":
                return self.fetch_500_data(lottery_type, period, page_size, headers)
            else:
                return self.fetch_cwl_data(lottery_type, period, page_size, headers)
                
        except Exception as e:
            error_msg = f"获取{lottery_type}数据失败: {str(e)}"
            print(f"API请求总错误: {error_msg}")
            return error_msg

    def fetch_500_data(self, lottery_type, period, page_size, headers):
        """从500网获取数据"""
        try:
            print(f"正在从500网获取{lottery_type}数据...")
            
            # 获取最新期号
            latest_period = self.get_latest_period_500(lottery_type)
            
            # 计算开始期号
            start_period = str(int(latest_period) - page_size + 1)
            
            # 构建API URL
            config = LOTTERY_API_CONFIG[lottery_type]
            url = f"{config['api_url']}?start={start_period}&end={latest_period}&limit={page_size}"
            
            print(f"请求URL: {url}")
            
            # 设置编码
            headers['Accept-Encoding'] = 'gzip, deflate'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'gb2312'  # 设置正确的编码
            
            if response.status_code == 200:
                # 解析HTML表格数据
                return self.parse_500_html(response.text, lottery_type, page_size)
            else:
                print(f"500网请求失败: {response.status_code}")
                error_info = f"500网HTTP请求失败: {response.status_code}"
                return self.generate_error_message(lottery_type, period, error_info)
                
        except Exception as e:
            print(f"500网数据获取异常: {str(e)}")
            error_info = f"500网数据获取异常: {str(e)}"
            return self.generate_error_message(lottery_type, period, error_info)

    def get_latest_period_500(self, lottery_type):
        """获取500网最新期号"""
        try:
            if lottery_type == "双色球":
                url = "https://datachart.500.com/ssq/history"
            else:
                url = "https://datachart.500.com/dlt/history"
            
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.encoding = 'gb2312'
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找期号输入框
            period_input = soup.find('input', {'id': 'end'})
            if period_input:
                latest_period = period_input.get('value', '')
                if latest_period:
                    print(f"{lottery_type}最新期号: {latest_period}")
                    return latest_period
            
            # 备用方法：根据当前日期生成期号
            from datetime import datetime
            today = datetime.now()
            return f"{today.year}{today.month:02d}{today.day:02d}"
            
        except Exception as e:
            print(f"获取最新期号失败: {e}")
            # 备用方法：根据当前日期生成期号
            from datetime import datetime
            today = datetime.now()
            return f"{today.year}{today.month:02d}{today.day:02d}"

    def get_headers(self):
        """获取请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def fetch_cwl_data(self, lottery_type, period, page_size, headers):
        """从福利彩票官网获取数据"""
        try:
            print(f"正在从福利彩票官网获取{lottery_type}数据...")
            
            config = BACKUP_LOTTERY_API_CONFIG[lottery_type]
            params = config["params"].copy()
            params["pageSize"] = page_size
            
            # 更新Referer
            headers["Referer"] = "https://www.cwl.gov.cn/"
            
            response = requests.get(
                config["api_url"],
                params=params,
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("state") == 0 and "result" in data:
                    return self.format_lottery_data(data["result"], lottery_type)
                else:
                    error_msg = f"API返回错误: {data.get('message', '未知错误')}"
                    print(f"福利彩票API错误: {error_msg}")
                    return self.generate_error_message(lottery_type, period, error_msg)
            else:
                error_msg = f"福利彩票API请求失败: {response.status_code}"
                print(f"福利彩票API HTTP错误: {error_msg}")
                return self.generate_error_message(lottery_type, period, error_msg)
                
        except Exception as e:
            print(f"福利彩票API请求异常: {str(e)}")
            return self.generate_error_message(lottery_type, period, str(e))

    def parse_500_html(self, html_content, lottery_type, page_size):
        """解析500网HTML数据"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html_content, 'html.parser')
            lottery_data = []
            
            # 查找数据表格 - 使用示例代码中的方法
            if lottery_type in ["双色球", "大乐透"]:
                tbody = soup.find('tbody', {'id': 'tdata'})
                if tbody:
                    rows = tbody.find_all('tr')
                else:
                    # 备用方法：查找所有表格
                    table = soup.find('table', {'class': 'tdata'})
                    if table:
                        rows = table.find_all('tr')[1:]  # 跳过表头
                    else:
                        rows = []
            else:
                rows = []
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                try:
                    # 解析期号
                    period = cells[0].get_text().strip()
                    if not period or period == '注数':
                        continue
                    
                    # 解析开奖号码
                    if lottery_type == "双色球":
                        # 双色球：6个红球 + 1个蓝球
                        red_balls = [int(cells[i+1].get_text().strip()) for i in range(6)]
                        blue_balls = [int(cells[7].get_text().strip())]
                        
                        item = {
                            "code": period,
                            "date": self._extract_date_from_period(period),
                            "red": ",".join(map(str, red_balls)),
                            "blue": str(blue_balls[0])
                        }
                        lottery_data.append(item)
                        
                    elif lottery_type == "大乐透":
                        # 大乐透：5个红球 + 2个蓝球
                        red_balls = [int(cells[i+1].get_text().strip()) for i in range(5)]
                        blue_balls = [int(cells[i+6].get_text().strip()) for i in range(2)]
                        
                        item = {
                            "code": period,
                            "date": self._extract_date_from_period(period),
                            "front": ",".join(map(str, red_balls)),
                            "back": ",".join(map(str, blue_balls))
                        }
                        lottery_data.append(item)
                    
                except (ValueError, IndexError) as e:
                    print(f"解析行数据失败: {e}")
                    continue
            
            # 限制数据量
            lottery_data = lottery_data[:page_size]
            
            if lottery_data:
                print(f"成功从500网获取{len(lottery_data)}期{lottery_type}数据")
                return self.format_lottery_data(lottery_data, lottery_type)
            else:
                print("500网数据解析失败，无有效数据")
                error_info = "500网数据解析失败：未提取到有效的开奖数据"
                return self.generate_error_message(lottery_type, f"最近{page_size}期", error_info)
                
        except Exception as e:
            print(f"500网HTML解析失败: {str(e)}")
            error_info = f"500网HTML解析失败: {str(e)}"
            return self.generate_error_message(lottery_type, f"最近{page_size}期", error_info)

    def _extract_date_from_period(self, period):
        """从期号中提取日期"""
        try:
            if len(period) >= 8:
                year = period[:4]
                month = period[4:6] if len(period) >= 6 else '01'
                day = period[6:8] if len(period) >= 8 else '01'
                return f"{year}-{month}-{day}"
            else:
                # 如果期号格式不标准，返回当前日期
                from datetime import datetime
                return datetime.now().strftime('%Y-%m-%d')
        except:
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')

    def try_backup_api(self, lottery_type, period, page_size, headers):
        """尝试备用API（福利彩票官网）"""
        try:
            print(f"尝试备用API（福利彩票官网）获取{lottery_type}数据...")
            
            # 使用福利彩票官网API
            return self.fetch_cwl_data(lottery_type, period, page_size, headers)
            
        except Exception as e:
            print(f"备用API总错误: {str(e)}")
            error_info = f"备用API（福利彩票官网）请求失败: {str(e)}"
            return self.generate_error_message(lottery_type, period, error_info)

    def generate_error_message(self, lottery_type, period, error_info):
        """生成错误信息"""
        error_msg = f"""
❌ {lottery_type}历史数据获取失败

📊 请求信息：
• 彩票类型：{lottery_type}
• 请求期数：{period}
• 数据源：500网 (datachart.500.com)
• 备用数据源：中国福利彩票官网 (cwl.gov.cn)

🔍 错误详情：
{error_info}

💡 解决建议：
1. 检查网络连接是否正常
2. 确认500网和福利彩票官网是否可访问
3. 稍后重试获取数据
4. 如果问题持续，请联系技术支持

🔄 操作选项：
• 点击"刷新数据"重试
• 点击"强制更新"忽略缓存重试
• 检查网络设置
        """
        return error_msg

    def format_lottery_data(self, raw_data, lottery_type):
        """格式化彩票数据"""
        try:
            formatted_data = f"📊 {lottery_type}历史开奖数据\n\n"
            formatted_data += "期号\t\t开奖日期\t\t开奖号码\n"
            formatted_data += "-" * 60 + "\n"
            
            # 统计号码频率
            number_stats = {}
            
            for item in raw_data:
                draw_number = item.get("code", "")
                draw_date = item.get("date", "")
                
                if lottery_type == "双色球":
                    red_numbers = item.get("red", "").split(",")
                    blue_number = item.get("blue", "")
                    numbers_str = f"{'-'.join(red_numbers)}+{blue_number}"
                    
                    # 统计红球
                    for num in red_numbers:
                        if num.isdigit():
                            num_int = int(num)
                            number_stats[num_int] = number_stats.get(num_int, 0) + 1
                    
                    # 统计蓝球
                    if blue_number.isdigit():
                        blue_int = int(blue_number)
                        number_stats[f"蓝{blue_int}"] = number_stats.get(f"蓝{blue_int}", 0) + 1
                        
                elif lottery_type == "大乐透":
                    front_numbers = item.get("front", "").split(",")
                    back_numbers = item.get("back", "").split(",")
                    numbers_str = f"{'-'.join(front_numbers)}+{'-'.join(back_numbers)}"
                    
                    # 统计前区号码
                    for num in front_numbers:
                        if num.isdigit():
                            num_int = int(num)
                            number_stats[num_int] = number_stats.get(num_int, 0) + 1
                    
                    # 统计后区号码
                    for num in back_numbers:
                        if num.isdigit():
                            num_int = int(num)
                            number_stats[f"后{num_int}"] = number_stats.get(f"后{num_int}", 0) + 1
                
                formatted_data += f"{draw_number}\t\t{draw_date}\t\t{numbers_str}\n"
            
            # 添加统计信息
            formatted_data += "\n📈 号码统计信息\n"
            formatted_data += "-" * 40 + "\n"
            
            # 分离红球/前区和蓝球/后区统计
            main_numbers = {k: v for k, v in number_stats.items() if isinstance(k, int)}
            special_numbers = {k: v for k, v in number_stats.items() if isinstance(k, str)}
            
            if lottery_type == "双色球":
                formatted_data += "热门红球号码:\n"
                sorted_red = sorted(main_numbers.items(), key=lambda x: x[1], reverse=True)[:10]
                for num, count in sorted_red:
                    formatted_data += f"  {num:2d}号: {count:2d}次\n"
                
                formatted_data += "\n热门蓝球号码:\n"
                sorted_blue = sorted(special_numbers.items(), key=lambda x: x[1], reverse=True)[:5]
                for num, count in sorted_blue:
                    blue_num = num.replace("蓝", "")
                    formatted_data += f"  {blue_num:2s}号: {count:2d}次\n"
                    
            elif lottery_type == "大乐透":
                formatted_data += "热门前区号码:\n"
                sorted_front = sorted(main_numbers.items(), key=lambda x: x[1], reverse=True)[:10]
                for num, count in sorted_front:
                    formatted_data += f"  {num:2d}号: {count:2d}次\n"
                
                formatted_data += "\n热门后区号码:\n"
                sorted_back = sorted(special_numbers.items(), key=lambda x: x[1], reverse=True)[:5]
                for num, count in sorted_back:
                    back_num = num.replace("后", "")
                    formatted_data += f"  {back_num:2s}号: {count:2d}次\n"
            
            formatted_data += f"\n💡 分析提示:\n"
            formatted_data += f"• 数据来源: 中国福利彩票官网\n"
            formatted_data += f"• 统计期数: {len(raw_data)}期\n"
            formatted_data += f"• 可用于分析号码走势和冷热号分布\n"
            
            return formatted_data
            
        except Exception as e:
            return f"格式化数据失败: {str(e)}"

    def get_history_data_for_analysis(self):
        """获取历史数据用于预测分析"""
        try:
            lottery_type = self.lottery_type_combo.currentText()
            period = self.period_combo.currentText()
            
            # 首先检查缓存
            cached_data = self.get_cached_history_data(lottery_type, period)
            if cached_data:
                return cached_data
            
            # 如果没有缓存或缓存过期，从真实API获取
            history_data = self.fetch_real_lottery_data(lottery_type, period)
            
            # 保存到本地缓存
            self.save_history_data(lottery_type, period, history_data)
            
            return history_data
            
        except Exception as e:
            # 如果获取历史数据失败，返回默认提示
            return f"历史数据获取失败：{str(e)}\n\n将基于AI知识进行预测分析。"
        """加载历史开奖数据"""
        lottery_type = self.lottery_type_combo.currentText()
        period = self.period_combo.currentText()
        
        # 显示加载提示
        loading_text = f"正在加载{lottery_type}{period}历史数据...\n\n请稍候，正在通过AI获取真实开奖数据..."
        self.history_table.setPlainText(loading_text)
        
        # 异步加载历史数据
        self.refresh_history_data()

    def refresh_history_data(self):
        """刷新历史数据"""
        lottery_type = self.lottery_type_combo.currentText()
        period = self.period_combo.currentText()
        
        # 禁用刷新按钮
        self.refresh_history_button.setEnabled(False)
        self.refresh_history_button.setText("🔄 获取中...")
        
        # 显示进度条
        self.history_progress.setVisible(True)
        self.history_progress.setRange(0, 0)  # 无限进度条
        
        # 显示加载状态
        self.history_table.setPlainText(f"正在获取{lottery_type}{period}历史数据...\n\n请稍候，正在从500网获取真实开奖数据...\n\n如果API请求失败，将显示详细错误信息。")
        
        # 检查缓存
        cached_data = self.get_cached_history_data(lottery_type, period)
        if cached_data:
            # 使用缓存数据
            self.history_table.setPlainText(cached_data)
            self.refresh_history_button.setEnabled(True)
            self.force_refresh_button.setEnabled(True)
            self.refresh_history_button.setText("🔄 刷新数据")
            self.force_refresh_button.setText("🔄 强制更新")
            self.history_progress.setVisible(False)
            self.status_bar.setText(f"✅ {lottery_type}{period}历史数据加载完成并已缓存")
        else:
            # 从真实API获取新数据
            self.request_real_history_data(lottery_type, period)

    def build_history_prompt(self, lottery_type, period):
        """构建历史数据请求提示词"""
        if lottery_type == "双色球":
            return f"""你是一位专业的彩票数据分析专家。请提供{period}双色球真实开奖数据。

要求：
1. 提供真实的历史开奖数据，包括期号、开奖日期、红球号码、蓝球号码
2. 数据格式要清晰易读，使用表格形式展示
3. 包含号码统计信息（热门号码、冷门号码等）
4. 提供数据分析建议

输出格式：
【历史开奖数据】
期号    开奖日期    红球号码    蓝球
XXXX    XXXX-XX-XX    XX-XX-XX-XX-XX-XX    XX

【号码统计】
热门红球：XX(次数), XX(次数)...
热门蓝球：XX(次数), XX(次数)...

【分析建议】
• 号码走势分析
• 冷热号分布
• 投注建议

请确保数据真实准确，格式清晰易读。"""
        else:
            return f"""你是一位专业的彩票数据分析专家。请提供{period}大乐透真实开奖数据。

要求：
1. 提供真实的历史开奖数据，包括期号、开奖日期、前区号码、后区号码
2. 数据格式要清晰易读，使用表格形式展示
3. 包含号码统计信息（热门号码、冷门号码等）
4. 提供数据分析建议

输出格式：
【历史开奖数据】
期号    开奖日期    前区号码    后区号码
XXXX    XXXX-XX-XX    XX-XX-XX-XX-XX    XX-XX

【号码统计】
热门前区：XX(次数), XX(次数)...
热门后区：XX(次数), XX(次数)...

【分析建议】
• 号码走势分析
• 冷热号分布
• 投注建议

请确保数据真实准确，格式清晰易读。"""

    def request_history_data(self, prompt):
        """请求历史数据"""
        # 使用QTimer延迟执行，避免界面卡顿
        from PyQt5.QtCore import QTimer
        
        def make_request():
            try:
                # 使用当前选择的模型
                selected_model = self.model_combo.currentText()
                
                headers = {
                    "Authorization": f"Bearer {YUNWU_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": selected_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
                
                # 发送请求
                resp = requests.post(YUNWU_API_URL, headers=headers, json=data, timeout=60)
                resp.raise_for_status()
                result = resp.json()
                history_data = result.get("choices", [{}])[0].get("message", {}).get("content", "获取历史数据失败，请稍后重试。")
                
                # 保存到本地缓存
                lottery_type = self.lottery_type_combo.currentText()
                period = self.period_combo.currentText()
                self.save_history_data(lottery_type, period, history_data)
                
                # 显示历史数据
                self.history_table.setPlainText(history_data)
                
                # 恢复按钮状态
                self.refresh_history_button.setEnabled(True)
                self.force_refresh_button.setEnabled(True)
                self.refresh_history_button.setText("🔄 刷新数据")
                self.force_refresh_button.setText("🔄 强制更新")
                
                # 隐藏进度条
                self.history_progress.setVisible(False)
                
                # 更新状态栏和缓存状态
                self.status_bar.setText(f"✅ {lottery_type}{period}历史数据加载完成并已缓存")
                self.update_cache_status("已缓存", "green")
                
            except Exception as e:
                # 显示错误信息
                error_text = f"获取历史数据失败：{str(e)}\n\n请检查网络连接或稍后重试。"
                self.history_table.setPlainText(error_text)
                
                # 恢复按钮状态
                self.refresh_history_button.setEnabled(True)
                self.force_refresh_button.setEnabled(True)
                self.refresh_history_button.setText("🔄 刷新数据")
                self.force_refresh_button.setText("🔄 强制更新")
                
                # 隐藏进度条
                self.history_progress.setVisible(False)
                
                # 更新状态栏
                self.status_bar.setText("❌ 历史数据获取失败，请重试")
        
        # 延迟100ms执行，让界面有时间更新
        QTimer.singleShot(100, make_request)

    def request_real_history_data(self, lottery_type, period):
        """请求真实历史数据"""
        # 使用QTimer延迟执行，避免界面卡顿
        from PyQt5.QtCore import QTimer
        
        def make_request():
            try:
                # 从真实API获取数据
                history_data = self.fetch_real_lottery_data(lottery_type, period)
                
                # 保存到本地缓存
                self.save_history_data(lottery_type, period, history_data)
                
                # 显示历史数据
                self.history_table.setPlainText(history_data)
                
                # 恢复按钮状态
                self.refresh_history_button.setEnabled(True)
                self.force_refresh_button.setEnabled(True)
                self.refresh_history_button.setText("🔄 刷新数据")
                self.force_refresh_button.setText("🔄 强制更新")
                
                # 隐藏进度条
                self.history_progress.setVisible(False)
                
                # 更新状态栏和缓存状态
                self.status_bar.setText(f"✅ {lottery_type}{period}历史数据加载完成并已缓存")
                self.update_cache_status("已缓存", "green")
                
            except Exception as e:
                # 显示错误信息
                error_text = f"获取历史数据失败：{str(e)}\n\n请检查网络连接或稍后重试。"
                self.history_table.setPlainText(error_text)
                
                # 恢复按钮状态
                self.refresh_history_button.setEnabled(True)
                self.force_refresh_button.setEnabled(True)
                self.refresh_history_button.setText("🔄 刷新数据")
                self.force_refresh_button.setText("🔄 强制更新")
                
                # 隐藏进度条
                self.history_progress.setVisible(False)
                
                # 更新状态栏
                self.status_bar.setText("❌ 历史数据获取失败，请重试")
                self.update_cache_status("获取失败", "red")
        
        # 延迟100ms执行，让界面有时间更新
        QTimer.singleShot(100, make_request)

    def force_refresh_history_data(self):
        """强制刷新历史数据（忽略缓存）"""
        lottery_type = self.lottery_type_combo.currentText()
        period = self.period_combo.currentText()
        
        # 禁用按钮
        self.refresh_history_button.setEnabled(False)
        self.force_refresh_button.setEnabled(False)
        self.force_refresh_button.setText("🔄 更新中...")
        
        # 显示进度条
        self.history_progress.setVisible(True)
        self.history_progress.setRange(0, 0)  # 无限进度条
        
        # 显示加载状态
        self.history_table.setPlainText(f"正在强制更新{lottery_type}{period}历史数据...\n\n请稍候，正在从500网获取最新开奖数据...\n\n如果API请求失败，将显示详细错误信息。")
        
        # 更新缓存状态
        self.update_cache_status("更新中", "orange")
        
        # 从真实API获取新数据
        self.request_real_history_data(lottery_type, period)

    def on_lottery_type_changed(self):
        """彩票类型切换时更新历史数据"""
        self.load_history_data()

    def on_period_changed(self):
        """期数选择变化时更新历史数据"""
        self.load_history_data()

    def load_models(self):
        """加载可用模型列表"""
        try:
            # 使用http.client获取模型列表
            conn = http.client.HTTPSConnection("yunwu.ai")
            payload = ''
            headers = {
                'Authorization': YUNWU_API_KEY,
                'content-type': 'application/json'
            }
            conn.request("GET", "/v1/models", payload, headers)
            res = conn.getresponse()
            data = res.read()
            models_data = json.loads(data.decode("utf-8"))
            
            # 解析模型列表
            if "data" in models_data:
                for model in models_data["data"]:
                    if "id" in model:
                        self.available_models.append(model["id"])
            
            # 如果获取失败，使用默认模型
            if not self.available_models:
                self.available_models = [
                    "deepseek-r1-250528",
                    "deepseek-chat",
                    "qwen-turbo",
                    "qwen-plus",
                    "qwen-max"
                ]
            
            # 添加到下拉框
            self.model_combo.addItems(self.available_models)
            
        except Exception as e:
            # 如果API调用失败，使用默认模型
            self.available_models = [
                "deepseek-r1-250528",
                "deepseek-chat",
                "qwen-turbo",
                "qwen-plus",
                "qwen-max"
            ]
            self.model_combo.addItems(self.available_models)
            print(f"加载模型列表失败，使用默认模型: {str(e)}")

    def extract_numbers_from_prediction(self, prediction_text):
        """从预测结果中提取号码"""
        numbers = []
        invalid_groups = []  # 记录无效的号码组
        seen_combinations = set()  # 用于去重
        
        # 双色球号码提取模式（适配GLM 4.5输出格式）
        ssq_patterns = [
            r'第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})',  # 第X组：XX-XX-XX-XX-XX-XX+XX
            r'(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})',  # 6+1格式
            r'红球[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[，,]\s*蓝球[：:]\s*(\d{1,2})',  # 红球蓝球格式
            r'【推荐号码】\s*第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})',  # 【推荐号码】格式
        ]
        
        # 大乐透号码提取模式（适配GLM 4.5输出格式）
        dlt_patterns = [
            r'第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})[-\s]*(\d{1,2})',  # 第X组：XX-XX-XX-XX-XX+XX-XX
            r'(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})[-\s]*(\d{1,2})',  # 5+2格式
            r'前区[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[，,]\s*后区[：:]\s*(\d{1,2})[-\s]*(\d{1,2})',  # 前区后区格式
            r'【推荐号码】\s*第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})[-\s]*(\d{1,2})',  # 【推荐号码】格式
        ]
        
        lottery_type = self.lottery_type_combo.currentText()
        
        if lottery_type == "双色球":
            patterns = ssq_patterns
        else:
            patterns = dlt_patterns
            
        for pattern in patterns:
            matches = re.findall(pattern, prediction_text)
            for match in matches:
                if len(match) >= 6:  # 至少6个号码
                    # 验证号码范围
                    valid_numbers = []
                    is_valid_group = True
                    invalid_reason = ""
                    
                    if lottery_type == "双色球":
                        # 验证红球1-33，蓝球1-16（双色球使用个位数格式）
                        if len(match) >= 7:  # 双色球需要7个号码
                            for i, num in enumerate(match):
                                try:
                                    num_int = int(num)
                                    if i < 6:  # 红球
                                        if 1 <= num_int <= 33:
                                            valid_numbers.append(num)
                                        else:
                                            is_valid_group = False
                                            invalid_reason = f"红球{num}超出范围(1-33)"
                                            break
                                    else:  # 蓝球
                                        if 1 <= num_int <= 16:
                                            valid_numbers.append(num)
                                        else:
                                            is_valid_group = False
                                            invalid_reason = f"蓝球{num}超出范围(1-16)"
                                            break
                                except ValueError:
                                    is_valid_group = False
                                    invalid_reason = f"号码{num}格式错误"
                                    break
                        else:
                            is_valid_group = False
                            invalid_reason = f"号码数量不足(需要7个，实际{len(match)}个)"
                    else:
                        # 验证前区01-35，后区01-12（大乐透使用两位数格式）
                        if len(match) >= 7:  # 大乐透需要7个号码
                            for i, num in enumerate(match):
                                try:
                                    num_int = int(num)
                                    if i < 5:  # 前区
                                        if 1 <= num_int <= 35:
                                            valid_numbers.append(num)
                                        else:
                                            is_valid_group = False
                                            invalid_reason = f"前区号码{num}超出范围(01-35)"
                                            break
                                    else:  # 后区
                                        if 1 <= num_int <= 12:
                                            valid_numbers.append(num)
                                        else:
                                            is_valid_group = False
                                            invalid_reason = f"后区号码{num}超出范围(01-12)"
                                            break
                                except ValueError:
                                    is_valid_group = False
                                    invalid_reason = f"号码{num}格式错误"
                                    break
                        else:
                            is_valid_group = False
                            invalid_reason = f"号码数量不足(需要7个，实际{len(match)}个)"
                    
                    # 只有所有号码都有效才添加
                    if is_valid_group and len(valid_numbers) >= 7:
                        # 创建号码组合的唯一标识（用于去重）
                        if lottery_type == "双色球":
                            # 双色球：红球排序 + 蓝球
                            red_balls = sorted([int(x) for x in valid_numbers[:6]])
                            blue_ball = int(valid_numbers[6])
                            combination_key = f"SSQ_{'-'.join(map(str, red_balls))}+{blue_ball}"
                        else:
                            # 大乐透：前区排序 + 后区排序
                            front_balls = sorted([int(x) for x in valid_numbers[:5]])
                            back_balls = sorted([int(x) for x in valid_numbers[5:7]])
                            combination_key = f"DLT_{'-'.join(map(str, front_balls))}+{'-'.join(map(str, back_balls))}"
                        
                        # 检查是否重复
                        if combination_key not in seen_combinations:
                            seen_combinations.add(combination_key)
                            numbers.append(valid_numbers)
                        else:
                            print(f"跳过重复号码组合: {combination_key}")
                    else:
                        # 记录无效的号码组
                        invalid_groups.append({
                            'numbers': match,
                            'reason': invalid_reason
                        })
        
        # 如果有无效号码组，显示警告
        if invalid_groups:
            warning_msg = f"⚠️ 检测到{len(invalid_groups)}组无效号码已被过滤：\n"
            for i, group in enumerate(invalid_groups, 1):
                numbers_str = '-'.join(group['numbers'])
                warning_msg += f"第{i}组: {numbers_str} - {group['reason']}\n"
            print(warning_msg)  # 在控制台显示警告
        
        # 如果去重后号码太少，给出警告
        if len(numbers) < 3:
            print(f"⚠️ 警告：去重后只有{len(numbers)}组号码，可能影响分析效果")
        
        return numbers

    def validate_secondary_prediction(self, prediction_text, lottery_type):
        """验证二次预测结果的完整性"""
        validation_msg = ""
        
        # 检查是否包含号码组合
        if lottery_type == "双色球":
            pattern = r'第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})'
        else:
            pattern = r'第\d+组[：:]\s*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[-\s]*(\d{1,2})[+\s]*(\d{1,2})[-\s]*(\d{1,2})'
        
        matches = re.findall(pattern, prediction_text)
        
        if not matches:
            validation_msg += "\n⚠️ 警告：二次预测结果中未检测到完整的号码组合！\n"
            validation_msg += "可能原因：\n"
            validation_msg += "1. AI输出格式不符合要求\n"
            validation_msg += "2. 号码组合不完整\n"
            validation_msg += "3. 格式错误\n"
            validation_msg += "建议重新进行二次预测。\n"
        else:
            validation_msg += f"\n✅ 检测到 {len(matches)} 组号码组合\n"
            
            # 验证号码范围
            valid_groups = 0
            for i, match in enumerate(matches, 1):
                is_valid = True
                if lottery_type == "双色球":
                    if len(match) >= 7:
                        for j, num in enumerate(match):
                            try:
                                num_int = int(num)
                                if j < 6:  # 红球
                                    if not (1 <= num_int <= 33):
                                        is_valid = False
                                        break
                                else:  # 蓝球
                                    if not (1 <= num_int <= 16):
                                        is_valid = False
                                        break
                            except ValueError:
                                is_valid = False
                                break
                    else:
                        is_valid = False
                else:
                    if len(match) >= 7:
                        for j, num in enumerate(match):
                            try:
                                num_int = int(num)
                                if j < 5:  # 前区
                                    if not (1 <= num_int <= 35):
                                        is_valid = False
                                        break
                                else:  # 后区
                                    if not (1 <= num_int <= 12):
                                        is_valid = False
                                        break
                            except ValueError:
                                is_valid = False
                                break
                    else:
                        is_valid = False
                
                if is_valid:
                    valid_groups += 1
                else:
                    validation_msg += f"⚠️ 第{i}组号码范围验证失败\n"
            
            if valid_groups > 0:
                validation_msg += f"✅ {valid_groups} 组号码通过验证\n"
            else:
                validation_msg += "❌ 所有号码组合验证失败\n"
        
        return validation_msg

    def analyze_number_frequency(self, numbers):
        """分析号码频率"""
        if not numbers:
            return {}
        
        lottery_type = self.lottery_type_combo.currentText()
        
        if lottery_type == "双色球":
            # 分析红球和蓝球频率
            red_balls = []
            blue_balls = []
            
            for number_group in numbers:
                if len(number_group) >= 7:
                    red_balls.extend(number_group[:6])  # 前6个是红球
                    blue_balls.append(number_group[6])  # 第7个是蓝球
            
            # 统计频率
            red_freq = {}
            blue_freq = {}
            
            for ball in red_balls:
                red_freq[ball] = red_freq.get(ball, 0) + 1
            
            for ball in blue_balls:
                blue_freq[ball] = blue_freq.get(ball, 0) + 1
            
            # 计算统计信息
            total_red_balls = len(red_balls)
            total_blue_balls = len(blue_balls)
            
            # 计算热门号码（出现频率最高的）
            hot_red_balls = sorted(red_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            hot_blue_balls = sorted(blue_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                'red_balls': red_freq,
                'blue_balls': blue_freq,
                'total_groups': len(numbers),
                'total_red_balls': total_red_balls,
                'total_blue_balls': total_blue_balls,
                'hot_red_balls': hot_red_balls,
                'hot_blue_balls': hot_blue_balls
            }
        else:
            # 分析前区和后区频率
            front_balls = []
            back_balls = []
            
            for number_group in numbers:
                if len(number_group) >= 7:
                    front_balls.extend(number_group[:5])  # 前5个是前区
                    back_balls.extend(number_group[5:7])  # 后2个是后区
            
            # 统计频率
            front_freq = {}
            back_freq = {}
            
            for ball in front_balls:
                front_freq[ball] = front_freq.get(ball, 0) + 1
            
            for ball in back_balls:
                back_freq[ball] = back_freq.get(ball, 0) + 1
            
            # 计算统计信息
            total_front_balls = len(front_balls)
            total_back_balls = len(back_balls)
            
            # 计算热门号码（出现频率最高的）
            hot_front_balls = sorted(front_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            hot_back_balls = sorted(back_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                'front_balls': front_freq,
                'back_balls': back_freq,
                'total_groups': len(numbers),
                'total_front_balls': total_front_balls,
                'total_back_balls': total_back_balls,
                'hot_front_balls': hot_front_balls,
                'hot_back_balls': hot_back_balls
            }

    def do_predict(self):
        if self.is_predicting:
            return
            
        selected_model = self.model_combo.currentText()
        lottery_type = self.lottery_type_combo.currentText()
        
        if not selected_model:
            QMessageBox.warning(self, "警告", "请先选择AI模型！")
            return
        
        # 开始预测
        self.is_predicting = True
        self.predict_button.setEnabled(False)
        self.secondary_predict_button.setEnabled(False)
        self.predict_button.setText("🔄 预测中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.status_bar.setText("🔄 正在结合历史数据进行预测分析，请稍候...")
        
        if lottery_type == "双色球":
            group_count = "5-10组"
            number_format = "每组6+1格式"
            lottery_desc = "中国福利彩票双色球"
        else:
            group_count = "5-10组"
            number_format = "每组5+2格式"
            lottery_desc = "中国体育彩票超级大乐透"

        # 获取历史数据用于分析
        history_data = self.get_history_data_for_analysis()
        
        prompt = (
            f"你是一位资深的彩票数据分析专家，拥有丰富的统计学和概率学知识。请基于历史开奖数据为{lottery_desc}进行专业的号码预测分析。\n\n"
            f"【历史数据分析】\n"
            f"{history_data}\n\n"
            f"任务要求：\n"
            f"1. 生成{group_count}号码组合，格式为{number_format}\n"
            f"2. 每个号码组合都需要详细的分析依据\n"
            f"3. 结合历史数据分析：\n"
            f"   - 基于历史数据的冷热号分析\n"
            f"   - 遗漏值分析和补号策略\n"
            f"   - 奇偶比例、大小比例分析\n"
            f"   - 连号、重号、跨度分析\n"
            f"   - 历史走势规律总结\n\n"
            f"重要规则：\n"
            f"{'红球号码范围：1-33，蓝球号码范围：1-16（使用个位数格式）' if lottery_type == '双色球' else '前区号码范围：01-35，后区号码范围：01-12（使用两位数格式）'}\n"
            f"请严格遵循号码范围，不要生成超出范围的号码！\n\n"
            f"【号码多样性要求】\n"
            f"1. 确保每组号码组合都不相同\n"
            f"2. 避免重复使用相同的号码组合\n"
            f"3. 号码分布要均匀，不要过于集中\n"
            f"4. 每组号码都要有独特的分析思路\n\n"
            f"输出格式：\n"
            f"【历史数据分析】\n"
            f"基于历史数据的详细分析...\n\n"
            f"【推荐号码】\n"
            f"{'第1组：XX-XX-XX-XX-XX-XX+XX' if lottery_type == '双色球' else '第1组：XX-XX-XX-XX-XX+XX-XX'}\n"
            f"{'第2组：XX-XX-XX-XX-XX-XX+XX' if lottery_type == '双色球' else '第2组：XX-XX-XX-XX-XX+XX-XX'}\n"
            f"...\n\n"
            f"【分析依据】\n"
            f"第1组分析：基于历史数据的详细选号理由\n"
            f"第2组分析：基于历史数据的详细选号理由\n"
            f"...\n\n"
            f"【综合评估】\n"
            f"基于历史数据的整体分析思路和风险评估\n\n"
            f"注意：请确保号码符合{lottery_desc}的选号规则，分析要客观理性，不承诺中奖。确保每组号码组合都不相同。"
        )

        headers = {
            "Authorization": f"Bearer {YUNWU_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": selected_model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            resp = requests.post(YUNWU_API_URL, headers=headers, json=data, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            prediction = result.get("choices", [{}])[0].get("message", {}).get("content", "预测失败，请稍后重试。")
            
            # 保存第一次预测结果
            self.first_prediction_result = prediction
            
            # 提取号码
            self.first_prediction_numbers = self.extract_numbers_from_prediction(prediction)
            
            # 检查提取的号码数量
            if not self.first_prediction_numbers:
                warning_text = "\n⚠️ 警告：未能从预测结果中提取到有效的号码组合！\n"
                warning_text += "可能原因：\n"
                if lottery_type == "双色球":
                    warning_text += "1. AI生成的号码超出范围（双色球红球01-33，蓝球01-16）\n"
                else:
                    warning_text += "1. AI生成的号码超出范围（大乐透前区01-35，后区01-12）\n"
                warning_text += "2. 号码格式不符合要求\n"
                warning_text += "3. 号码数量不足\n"
                warning_text += "请重新进行预测。\n"
                prediction += warning_text
            
            # 格式化输出
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_result = f"""
🎯 AI 彩票预测结果
{'='*50}

🤖 使用模型: {selected_model}
🎲 彩票类型: {lottery_type}
⏰ 预测时间: {current_time}

📊 预测分析:
{prediction}

{'='*50}
💡 温馨提示: 彩票有风险，投注需谨慎！
🎯 提示: 完成第一次预测后，可点击"二次预测"进行深度分析！
            """
            
            self.first_result_output.setPlainText(formatted_result.strip())
            
            # 切换到第一次预测标签页
            self.tab_widget.setCurrentIndex(0)
            
            # 启用二次预测按钮
            if self.first_prediction_numbers:
                self.secondary_predict_button.setEnabled(True)
                self.status_bar.setText(f"✅ 预测完成！成功提取到 {len(self.first_prediction_numbers)} 组号码，可进行二次预测")
                QMessageBox.information(self, "预测完成", f"第一次预测完成！\n\n成功提取到 {len(self.first_prediction_numbers)} 组号码\n\n现在可以进行二次预测分析！")
            else:
                self.status_bar.setText("⚠️ 预测完成，但未能提取到有效号码，请重新预测")
                QMessageBox.warning(self, "号码提取失败", "第一次预测完成，但未能提取到有效号码。\n\n请检查预测结果格式，或重新进行预测。")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预测失败: {str(e)}")
            self.first_result_output.setPlainText(f"❌ 预测失败: {str(e)}\n\n请检查网络连接或稍后重试。")
        
        finally:
            # 恢复按钮状态
            self.is_predicting = False
            self.predict_button.setEnabled(True)
            self.predict_button.setText("🚀 开始预测")
            self.progress_bar.setVisible(False)
            if not self.first_prediction_numbers:
                self.status_bar.setText("就绪 - 请选择AI模型和彩票类型开始预测")

    def do_secondary_predict(self):
        """执行二次预测"""
        if self.is_secondary_predicting:
            return
            
        if not self.first_prediction_result or not self.first_prediction_numbers:
            QMessageBox.warning(self, "警告", "请先完成第一次预测！")
            return
        
        selected_model = self.model_combo.currentText()
        lottery_type = self.lottery_type_combo.currentText()
        
        # 开始二次预测
        self.is_secondary_predicting = True
        self.secondary_predict_button.setEnabled(False)
        self.predict_button.setEnabled(False)
        self.secondary_predict_button.setText("🔄 分析中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.setText("🔄 正在结合历史数据进行二次分析，请稍候...")
        
        # 格式化第一次预测的号码
        numbers_text = ""
        for i, numbers in enumerate(self.first_prediction_numbers, 1):
            if lottery_type == "双色球":
                red_balls = numbers[:6]
                blue_ball = numbers[6] if len(numbers) > 6 else "?"
                numbers_text += f"第{i}组: {'-'.join(red_balls)}+{blue_ball}\n"
            else:
                front_balls = numbers[:5]
                back_balls = numbers[5:7] if len(numbers) > 5 else ["?", "?"]
                numbers_text += f"第{i}组: {'-'.join(front_balls)}+{'-'.join(back_balls)}\n"
        
        # 分析号码频率
        frequency_analysis = self.analyze_number_frequency(self.first_prediction_numbers)
        
        # 生成频率分析文本
        frequency_text = ""
        if lottery_type == "双色球" and frequency_analysis:
            red_freq = frequency_analysis.get('red_balls', {})
            blue_freq = frequency_analysis.get('blue_balls', {})
            hot_red_balls = frequency_analysis.get('hot_red_balls', [])
            hot_blue_balls = frequency_analysis.get('hot_blue_balls', [])
            total_groups = frequency_analysis.get('total_groups', 0)
            
            frequency_text += "\n📊 号码频率统计分析:\n"
            frequency_text += f"📈 分析组数: {total_groups}组\n"
            frequency_text += f"🔴 红球总数: {frequency_analysis.get('total_red_balls', 0)}个\n"
            frequency_text += f"🔵 蓝球总数: {frequency_analysis.get('total_blue_balls', 0)}个\n\n"
            
            frequency_text += "🔥 热门红球号码:\n"
            for ball, freq in hot_red_balls:
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "🔥 热门蓝球号码:\n"
            for ball, freq in hot_blue_balls:
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "\n📋 完整频率分布:\n"
            frequency_text += "红球频率:\n"
            for ball, freq in sorted(red_freq.items(), key=lambda x: x[1], reverse=True):
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "蓝球频率:\n"
            for ball, freq in sorted(blue_freq.items(), key=lambda x: x[1], reverse=True):
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
                
        elif lottery_type == "大乐透" and frequency_analysis:
            front_freq = frequency_analysis.get('front_balls', {})
            back_freq = frequency_analysis.get('back_balls', {})
            hot_front_balls = frequency_analysis.get('hot_front_balls', [])
            hot_back_balls = frequency_analysis.get('hot_back_balls', [])
            total_groups = frequency_analysis.get('total_groups', 0)
            
            frequency_text += "\n📊 号码频率统计分析:\n"
            frequency_text += f"📈 分析组数: {total_groups}组\n"
            frequency_text += f"🔴 前区总数: {frequency_analysis.get('total_front_balls', 0)}个\n"
            frequency_text += f"🔵 后区总数: {frequency_analysis.get('total_back_balls', 0)}个\n\n"
            
            frequency_text += "🔥 热门前区号码:\n"
            for ball, freq in hot_front_balls:
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "🔥 热门后区号码:\n"
            for ball, freq in hot_back_balls:
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "\n📋 完整频率分布:\n"
            frequency_text += "前区频率:\n"
            for ball, freq in sorted(front_freq.items(), key=lambda x: x[1], reverse=True):
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
            
            frequency_text += "后区频率:\n"
            for ball, freq in sorted(back_freq.items(), key=lambda x: x[1], reverse=True):
                percentage = (freq / total_groups * 100) if total_groups > 0 else 0
                frequency_text += f"  {ball}号: {freq}次 ({percentage:.1f}%)\n"
        
        # 获取历史数据用于二次分析
        history_data = self.get_history_data_for_analysis()
        
        # 构建二次预测提示词
        if lottery_type == "双色球":
            secondary_prompt = f"""你是一位资深的彩票数据分析专家，具备强大的统计分析和概率计算能力。请基于历史数据和以下双色球预测结果进行深度分析，重新组合出最优的号码组合。

【历史数据分析】
{history_data}

【原始预测数据】
第一次预测结果：
{self.first_prediction_result}

【号码组合统计】
提取的号码组合：
{numbers_text}{frequency_text}

【分析任务】
请基于历史数据和以上预测结果，运用统计学和概率学原理，重新组合出1-2组最优号码。

【分析步骤】
1. 历史数据分析：结合历史开奖数据，分析号码走势规律
2. 频率分析：基于号码出现频率，识别热门号码和冷门号码
3. 特征分析：分析奇偶比例、大小比例、连号情况等特征
4. 分布优化：确保号码分布均匀，避免过于集中
5. 概率计算：结合历史规律，计算最优组合概率
6. 规则验证：确保符合双色球选号规则（红球1-33，蓝球1-16）

重要提醒：请严格遵循号码范围，红球只能在1-33中选择，蓝球只能在1-16中选择！

【输出格式要求】
你必须严格按照以下格式输出，确保包含完整的号码组合：

【历史数据分析】
基于历史数据的详细分析...

【重新组合结果】
第1组：XX-XX-XX-XX-XX-XX+XX
第2组：XX-XX-XX-XX-XX-XX+XX（如有）

【选择理由】
详细说明每个号码的选择依据，包括：
- 历史数据分析结果
- 频率分析结果
- 特征匹配情况
- 概率学依据
- 历史规律参考

【概率评估】
- 基于历史数据的中奖概率分析
- 风险评估
- 投资建议

【注意事项】
- 基于历史数据和频率分析重新组合，不是简单选择
- 确保号码符合双色球规则
- 分析要客观理性，不承诺中奖
- 必须输出完整的号码组合，不能只输出数字"""
        else:
            secondary_prompt = f"""你是一位资深的彩票数据分析专家，具备强大的统计分析和概率计算能力。请基于历史数据和以下大乐透预测结果进行深度分析，重新组合出最优的号码组合。

【历史数据分析】
{history_data}

【原始预测数据】
第一次预测结果：
{self.first_prediction_result}

【号码组合统计】
提取的号码组合：
{numbers_text}{frequency_text}

【分析任务】
请基于历史数据和以上预测结果，运用统计学和概率学原理，重新组合出1-2组最优号码。

【分析步骤】
1. 历史数据分析：结合历史开奖数据，分析号码走势规律
2. 频率分析：基于号码出现频率，识别热门号码和冷门号码
3. 特征分析：分析奇偶比例、大小比例、连号情况等特征
4. 分布优化：确保号码分布均匀，避免过于集中
5. 概率计算：结合历史规律，计算最优组合概率
6. 规则验证：确保符合大乐透选号规则（前区01-35，后区01-12）

重要提醒：请严格遵循号码范围，前区只能在01-35中选择，后区只能在01-12中选择！

【输出格式要求】
你必须严格按照以下格式输出，确保包含完整的号码组合：

【历史数据分析】
基于历史数据的详细分析...

【重新组合结果】
第1组：XX-XX-XX-XX-XX+XX-XX
第2组：XX-XX-XX-XX-XX+XX-XX（如有）

【选择理由】
详细说明每个号码的选择依据，包括：
- 历史数据分析结果
- 频率分析结果
- 特征匹配情况
- 概率学依据
- 历史规律参考

【概率评估】
- 基于历史数据的中奖概率分析
- 风险评估
- 投资建议

【注意事项】
- 基于历史数据和频率分析重新组合，不是简单选择
- 确保号码符合大乐透规则
- 分析要客观理性，不承诺中奖
- 必须输出完整的号码组合，不能只输出数字"""

        headers = {
            "Authorization": f"Bearer {YUNWU_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": selected_model,
            "messages": [
                {"role": "user", "content": secondary_prompt}
            ]
        }
        
        try:
            resp = requests.post(YUNWU_API_URL, headers=headers, json=data, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            secondary_prediction = result.get("choices", [{}])[0].get("message", {}).get("content", "二次预测失败，请稍后重试。")
            
            # 验证二次预测结果的完整性
            validation_result = self.validate_secondary_prediction(secondary_prediction, lottery_type)
            
            # 格式化输出
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_result = f"""
🎯 二次预测分析结果
{'='*50}

🤖 使用模型: {selected_model}
🎲 彩票类型: {lottery_type}
⏰ 分析时间: {current_time}

📊 第一次预测号码:
{numbers_text}

📈 号码频率分析:
{frequency_text}

🔍 重新组合结果:
{secondary_prediction}

{validation_result}

{'='*50}
💡 温馨提示: 彩票有风险，投注需谨慎！
🎯 二次预测基于号码频率分析重新组合，提高中奖概率！
            """
            
            self.secondary_result_output.setPlainText(formatted_result.strip())
            
            # 切换到二次预测标签页
            self.tab_widget.setCurrentIndex(1)
            
            QMessageBox.information(self, "二次预测完成", "二次预测分析完成！\n\n已从第一次预测结果中筛选出最具潜力的号码组合。\n\n请查看二次预测结果标签页。")
            
            # 更新状态栏
            self.status_bar.setText("✅ 基于历史数据的二次预测分析完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"二次预测失败: {str(e)}")
            self.secondary_result_output.setPlainText(f"❌ 二次预测失败: {str(e)}\n\n请检查网络连接或稍后重试。")
            
            # 更新状态栏
            self.status_bar.setText("❌ 二次预测失败，请重试")
        
        finally:
            # 恢复按钮状态
            self.is_secondary_predicting = False
            self.secondary_predict_button.setEnabled(True)
            self.predict_button.setEnabled(True)
            self.secondary_predict_button.setText("🎯 二次预测")
            self.progress_bar.setVisible(False)

if __name__ == "__main__":
    try:
        print("正在启动AI彩票预测程序...")
        
        app = QApplication(sys.argv)
        print("QApplication创建成功")
        
        # 设置应用样式
        app.setStyle('Fusion')
        print("应用样式设置完成")
        
        print("正在创建主窗口...")
        window = PredictorWindow()
        print("主窗口创建成功")
        
        print("正在显示窗口...")
        window.show()
        print("窗口显示成功")
        
        print("程序启动完成，进入事件循环...")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 保持窗口打开以便查看错误
        input("按回车键退出...") 