import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import io
import time
import re
import gc
import pytz
from datetime import datetime, timedelta
from dateutil.parser import parse

# 解决Streamlit警告问题
# st.set_option('deprecation.showPyplotGlobalUse', False)

# 页面设置
st.set_page_config(
    page_title="Advanced Chart Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用标题
st.title("📊 Advanced Chart Generator & Analyzer")
st.markdown("""
**上传您的数据，创建精美的图表，并进行数据分析。**  
支持大数据量处理、多种日期/时间格式和时间序列分析。
""")

# 创建示例数据（包含多种日期格式）
@st.cache_data
def create_sample_data(size=1000):
    # 创建多种日期格式
    base_date = datetime(2023, 1, 1)
    dates = [base_date + timedelta(days=i) for i in range(size)]
    
    # 创建多种日期格式
    date_formats = {
        'ISO_Date': [d.isoformat() for d in dates],
        'US_Date': [d.strftime('%m/%d/%Y') for d in dates],
        'EU_Date': [d.strftime('%d/%m/%Y') for d in dates],
        'DateTime_Stamp': [d.timestamp() for d in dates],
        'Year_Month': [d.strftime('%Y-%m') for d in dates],
        'Full_DateTime': [d.strftime('%Y-%m-%d %H:%M:%S') for d in dates]
    }
    
    data = {
        'Sales': np.random.randint(100, 1000, size) * (1 + np.sin(np.arange(size)/10)),
        'Expenses': np.random.randint(50, 500, size) * (1 + np.cos(np.arange(size)/8)),
        'Visitors': np.random.randint(100, 500, size),
        'Region': np.random.choice(['North', 'South', 'East', 'West'], size),
        'Product': np.random.choice(['A', 'B', 'C', 'D'], size),
        'Category': np.random.choice(['Electronics', 'Clothing', 'Food', 'Furniture'], size)
    }
    
    # 合并日期格式
    data.update(date_formats)
    return pd.DataFrame(data)

# 自动检测日期列并转换
def auto_convert_datetime(df):
    date_cols = []
    converted_cols = {}
    
    # 尝试检测和转换日期列
    for col in df.columns:
        # 跳过数值列
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].max() > 1e9:
            # 可能是时间戳（秒）
            try:
                converted = pd.to_datetime(df[col], unit='s')
                df[col + '_datetime'] = converted
                converted_cols[col] = col + '_datetime'
                date_cols.append(col + '_datetime')
                continue
            except:
                pass
            
            # 尝试毫秒时间戳
            try:
                converted = pd.to_datetime(df[col], unit='ms')
                df[col + '_datetime'] = converted
                converted_cols[col] = col + '_datetime'
                date_cols.append(col + '_datetime')
                continue
            except:
                pass
        
        # 尝试解析为日期
        sample = df[col].dropna().sample(min(10, len(df[col].dropna())))
        date_count = 0
        
        for val in sample:
            try:
                # 尝试解析各种格式
                parse(str(val))
                date_count += 1
            except:
                pass
        
        # 如果大部分值可以解析为日期
        if date_count / len(sample) > 0.7:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                date_cols.append(col)
            except:
                pass
    
    return df, date_cols, converted_cols

# 分块读取大型CSV文件
def read_large_csv(file, chunksize=10000, sample_size=10000):
    chunk_list = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 获取文件大小
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    # 估算总行数
    total_chunks = (file_size // (chunksize * 100)) + 1
    
    for i, chunk in enumerate(pd.read_csv(file, chunksize=chunksize)):
        chunk_list.append(chunk)
        progress = min((i + 1) / total_chunks, 1.0)
        progress_bar.progress(progress)
        status_text.text(f"读取数据中... {progress*100:.1f}%")
        if len(pd.concat(chunk_list, ignore_index=True)) > sample_size:
            break
    
    df = pd.concat(chunk_list, ignore_index=True)
    progress_bar.empty()
    status_text.empty()
    
    # 如果数据量大于采样大小，则进行采样
    if len(df) > sample_size:
        st.info(f"数据集较大（{len(df)}行），已自动采样前{sample_size}行。可在高级选项中选择完整处理。")
        return df.head(sample_size)
    return df

# 读取Excel文件（带采样选项）
def read_excel_with_sampling(file, sample_size=10000):
    # 获取所有sheet名
    xl = pd.ExcelFile(file)
    sheet_names = xl.sheet_names
    
    # 让用户选择sheet
    if len(sheet_names) > 1:
        sheet_name = st.selectbox("选择工作表", sheet_names)
    else:
        sheet_name = sheet_names[0]
    
    # 获取总行数
    df_temp = pd.read_excel(file, sheet_name=sheet_name, nrows=1)
    total_rows = pd.read_excel(file, sheet_name=sheet_name, usecols=[0]).shape[0]
    
    # 如果行数过多，提示采样
    if total_rows > sample_size:
        st.info(f"Excel文件包含{total_rows}行数据，将采样前{sample_size}行。")
        df = pd.read_excel(file, sheet_name=sheet_name, nrows=sample_size)
    else:
        df = pd.read_excel(file, sheet_name=sheet_name)
    
    return df

# 初始化会话状态
if 'df' not in st.session_state:
    st.session_state.df = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'chart_type' not in st.session_state:
    st.session_state.chart_type = 'line'
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = 'summary'
if 'use_sampling' not in st.session_state:
    st.session_state.use_sampling = True
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = []
if 'date_columns' not in st.session_state:
    st.session_state.date_columns = []
if 'date_conversions' not in st.session_state:
    st.session_state.date_conversions = {}

# 侧边栏 - 文件上传和设置
with st.sidebar:
    st.header("📂 数据上传")
    uploaded_file = st.file_uploader("上传CSV或Excel文件", type=['csv', 'xlsx'], 
                                    help="支持最大200MB的文件")
    
    # 大数据处理选项
    st.markdown("---")
    st.header("⚙️ 大数据处理选项")
    st.session_state.use_sampling = st.checkbox("自动采样大数据集", value=True, 
                                              help="对于超过10,000行的数据集自动采样")
    sample_size = st.slider("采样大小", 1000, 50000, 10000, 1000,
                          help="设置自动采样的行数")
    
    process_full_data = st.checkbox("处理完整数据集（谨慎使用）", value=False,
                                  help="对于非常大的数据集可能会导致性能问题")
    
    st.markdown("---")
    st.header("📈 图表设置")
    chart_options = {
        '折线图': 'line',
        '柱状图': 'bar',
        '散点图': 'scatter',
        '饼图': 'pie',
        '箱线图': 'box',
        '热力图': 'heatmap',
        '面积图': 'area',
        '直方图': 'histogram',
        '时间序列图': 'timeseries'
    }
    chart_display_name = st.selectbox(
        "选择图表类型",
        list(chart_options.keys()))
    st.session_state.chart_type = chart_options[chart_display_name]
    
    st.markdown("---")
    st.header("🔍 分析设置")
    analysis_options = {
        '数据摘要': 'summary',
        '相关性分析': 'correlation',
        '时间序列分析': 'timeseries',
        '分类汇总': 'categorical'
    }
    analysis_display_name = st.selectbox(
        "选择分析类型",
        list(analysis_options.keys()))
    st.session_state.analysis_type = analysis_options[analysis_display_name]
    
    st.markdown("---")
    st.header("📅 日期设置")
    date_timezone = st.selectbox("时区设置", ['UTC', '本地时区', '选择时区...'])
    
    if date_timezone == '选择时区...':
        selected_tz = st.selectbox("选择时区", pytz.all_timezones)
    else:
        selected_tz = 'UTC' if date_timezone == 'UTC' else None
    
    st.markdown("---")
    st.header("🎨 主题设置")
    theme = st.selectbox("选择图表主题", ['plotly', 'seaborn', 'ggplot2', 'darkly'])
    
    st.markdown("---")
    st.caption("""
    **日期/时间处理指南:**
    1. 应用会自动检测日期/时间列
    2. 时间戳会自动转换为可读日期
    3. 可以使用日期范围选择器筛选数据
    4. 支持多种国际日期格式
    """)

# 数据处理
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            if st.session_state.use_sampling:
                st.session_state.df = read_large_csv(uploaded_file, sample_size=sample_size)
            else:
                with st.spinner('正在加载CSV文件，可能需要一些时间...'):
                    st.session_state.df = pd.read_csv(uploaded_file)
                st.success("CSV文件加载成功!")
                
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            with st.spinner('正在加载Excel文件...'):
                st.session_state.df = read_excel_with_sampling(uploaded_file, sample_size=sample_size)
            st.success("Excel文件加载成功!")
            
        # 保存原始数据副本
        st.session_state.original_df = st.session_state.df.copy()
        
        # 自动转换日期列
        with st.spinner('正在检测日期/时间列...'):
            st.session_state.df, st.session_state.date_columns, st.session_state.date_conversions = auto_convert_datetime(st.session_state.df)
            
        if st.session_state.date_columns:
            st.success(f"检测到 {len(st.session_state.date_columns)} 个日期/时间列")
        else:
            st.info("未检测到日期/时间列。可以使用下方的日期转换工具。")
        
    except Exception as e:
        st.error(f"错误读取文件: {str(e)}")
        st.session_state.df = None
else:
    data_size = st.slider("示例数据大小", 1000, 100000, 5000, 1000)
    if st.button("生成示例数据（含多种日期格式）"):
        with st.spinner(f'正在生成{data_size}行示例数据...'):
            st.session_state.df = create_sample_data(data_size)
            st.session_state.original_df = st.session_state.df.copy()
            
            # 自动转换日期列
            st.session_state.df, st.session_state.date_columns, st.session_state.date_conversions = auto_convert_datetime(st.session_state.df)
            
        st.success(f"成功生成{len(st.session_state.df)}行示例数据! 包含多种日期格式。")

# 数据显示
if st.session_state.df is not None:
    # 日期转换工具
    with st.expander("🔧 日期/时间转换工具", expanded=True):
        st.subheader("手动日期列转换")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            date_col = st.selectbox("选择要转换的列", st.session_state.df.columns)
        
        with col2:
            date_format = st.selectbox("日期格式", [
                '自动检测', 
                '时间戳(秒)', 
                '时间戳(毫秒)', 
                'ISO格式 (YYYY-MM-DD)', 
                '美国格式 (MM/DD/YYYY)',
                '欧洲格式 (DD/MM/YYYY)',
                '自定义'
            ])
            
            if date_format == '自定义':
                custom_format = st.text_input("输入自定义格式", "%Y-%m-%d %H:%M:%S")
        
        with col3:
            new_col_name = st.text_input("新列名称", f"{date_col}_converted")
        
        if st.button("转换日期列"):
            try:
                if date_format == '时间戳(秒)':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], unit='s', errors='coerce'
                    )
                elif date_format == '时间戳(毫秒)':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], unit='ms', errors='coerce'
                    )
                elif date_format == 'ISO格式 (YYYY-MM-DD)':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], format='%Y-%m-%d', errors='coerce'
                    )
                elif date_format == '美国格式 (MM/DD/YYYY)':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], format='%m/%d/%Y', errors='coerce'
                    )
                elif date_format == '欧洲格式 (DD/MM/YYYY)':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], format='%d/%m/%Y', errors='coerce'
                    )
                elif date_format == '自定义':
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], format=custom_format, errors='coerce'
                    )
                else:  # 自动检测
                    st.session_state.df[new_col_name] = pd.to_datetime(
                        st.session_state.df[date_col], errors='coerce'
                    )
                
                # 更新日期列列表
                if new_col_name not in st.session_state.date_columns:
                    st.session_state.date_columns.append(new_col_name)
                
                st.success(f"成功创建新日期列: {new_col_name}")
            except Exception as e:
                st.error(f"日期转换失败: {str(e)}")
        
        # 日期范围选择器
        st.subheader("日期范围筛选")
        if st.session_state.date_columns:
            date_col_selection = st.selectbox("选择日期列", st.session_state.date_columns)
            
            if st.session_state.df[date_col_selection].notnull().any():
                min_date = st.session_state.df[date_col_selection].min()
                max_date = st.session_state.df[date_col_selection].max()
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("开始日期", min_date)
                with col2:
                    end_date = st.date_input("结束日期", max_date)
                
                if st.button("应用日期筛选"):
                    # 转换为与数据相同的时区
                    if selected_tz:
                        start_date = pd.Timestamp(start_date).tz_localize(selected_tz)
                        end_date = pd.Timestamp(end_date).tz_localize(selected_tz)
                    
                    mask = (st.session_state.df[date_col_selection] >= pd.Timestamp(start_date)) & \
                           (st.session_state.df[date_col_selection] <= pd.Timestamp(end_date))
                    st.session_state.df = st.session_state.df.loc[mask]
                    st.success(f"筛选后数据: {len(st.session_state.df)}行")
            else:
                st.warning("选择的日期列包含空值，无法筛选")
        else:
            st.info("没有可用的日期列进行筛选")
    
    # 列选择器 - 减少处理的数据量
    with st.expander("🔍 列选择器 (选择要分析的列)", expanded=False):
        all_columns = st.session_state.df.columns.tolist()
        if not st.session_state.selected_columns:
            st.session_state.selected_columns = all_columns
        
        cols_per_row = 4
        cols = st.columns(cols_per_row)
        
        for i, column in enumerate(all_columns):
            with cols[i % cols_per_row]:
                if st.checkbox(column, value=column in st.session_state.selected_columns, key=f"col_{column}"):
                    if column not in st.session_state.selected_columns:
                        st.session_state.selected_columns.append(column)
                else:
                    if column in st.session_state.selected_columns:
                        st.session_state.selected_columns.remove(column)
        
        if st.button("应用列选择"):
            st.session_state.df = st.session_state.df[st.session_state.selected_columns].copy()
            st.rerun()
    
    # 数据处理选项
    with st.expander("⚙️ 数据处理选项", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("重置为完整数据集"):
                st.session_state.df = st.session_state.original_df.copy()
                st.session_state.selected_columns = st.session_state.original_df.columns.tolist()
                st.rerun()
            
        with col2:
            if st.button("清除内存"):
                gc.collect()
                st.success("已释放内存!")
    
    with st.expander("📄 数据预览", expanded=True):
        # 显示数据子集
        preview_size = st.slider("预览行数", 10, 1000, 100, 10)
        st.dataframe(st.session_state.df.head(preview_size))
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总行数", st.session_state.original_df.shape[0])
        col2.metric("当前行数", st.session_state.df.shape[0])
        col3.metric("总列数", st.session_state.original_df.shape[1])
        col4.metric("当前列数", st.session_state.df.shape[1])
        
        # 显示内存使用
        mem_usage = st.session_state.df.memory_usage(deep=True).sum() / (1024 ** 2)  # MB
        st.info(f"当前数据内存使用: {mem_usage:.2f} MB")
        
        # 显示日期列信息
        if st.session_state.date_columns:
            st.subheader("日期/时间列信息")
            date_info = []
            for col in st.session_state.date_columns:
                date_info.append({
                    '列名': col,
                    '最早日期': st.session_state.df[col].min(),
                    '最晚日期': st.session_state.df[col].max(),
                    '空值数量': st.session_state.df[col].isnull().sum()
                })
            st.dataframe(pd.DataFrame(date_info))
        
        # 显示数据类型
        st.subheader("数据类型摘要")
        dtype_df = pd.DataFrame({
            '列名': st.session_state.df.columns,
            '数据类型': st.session_state.df.dtypes.astype(str),
            '唯一值数量': st.session_state.df.nunique().values,
            '缺失值数量': st.session_state.df.isnull().sum().values
        })
        st.dataframe(dtype_df)
    
    st.markdown("---")
    
    # 图表配置
    st.header("⚙️ 图表配置")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        # 根据图表类型动态显示配置选项
        if st.session_state.chart_type in ['line', 'bar', 'scatter', 'area', 'timeseries']:
            # 优先使用日期列作为X轴
            x_options = st.session_state.date_columns + [col for col in st.session_state.df.columns if col not in st.session_state.date_columns]
            x_axis = st.selectbox("X轴", x_options)
            
            y_axis = st.selectbox("Y轴", st.session_state.df.columns)
            
            if st.session_state.chart_type == 'scatter':
                color_col = st.selectbox("颜色分组", ['无'] + list(st.session_state.df.columns))
                size_col = st.selectbox("大小分组", ['无'] + list(st.session_state.df.columns))
                hover_data = st.multiselect("悬停数据", st.session_state.df.columns)
            else:
                group_col = st.selectbox("分组列", ['无'] + list(st.session_state.df.columns))
            
            # 时间序列特定选项
            if st.session_state.chart_type == 'timeseries':
                resample_freq = st.selectbox("时间频率", 
                                           ['原始', '日', '周', '月', '季度', '年'],
                                           help="聚合时间序列数据")
                agg_method = st.selectbox("聚合方法", ['平均值', '总和', '最大值', '最小值'])
                
        elif st.session_state.chart_type == 'pie':
            names_col = st.selectbox("类别列", st.session_state.df.columns)
            values_col = st.selectbox("数值列", st.session_state.df.columns)
            hole_size = st.slider("中心孔洞大小", 0.0, 0.9, 0.0)
            
        elif st.session_state.chart_type == 'box':
            cat_col = st.selectbox("类别列", st.session_state.df.columns)
            val_col = st.selectbox("数值列", st.session_state.df.columns)
            
        elif st.session_state.chart_type == 'heatmap':
            st.info("热力图将显示数值列之间的相关性")
            annotate = st.checkbox("显示数值", True)
        
        elif st.session_state.chart_type == 'histogram':
            hist_col = st.selectbox("数值列", st.session_state.df.columns)
            bins = st.slider("分箱数量", 5, 100, 20)
            hist_group = st.selectbox("分组列 (可选)", ['无'] + list(st.session_state.df.columns))
        
        # 通用图表选项
        chart_title = st.text_input("图表标题", "数据分析图表")
        color_palette = st.selectbox("颜色方案", px.colors.named_colorscales())
        height = st.slider("图表高度", 400, 1000, 600)
        width = st.slider("图表宽度", 600, 1200, 800)
        
        # 大数据图表优化
        if len(st.session_state.df) > 10000:
            st.warning("大数据集图表提示: 考虑使用聚合或采样以获得更好性能")
            if st.session_state.chart_type != 'timeseries':
                agg_method = st.selectbox("聚合方法", ['无', '平均值', '总和', '计数'], 
                                        help="对大数据集进行聚合以提高性能")
            if agg_method != '无' or resample_freq != '原始':
                sample_data = st.checkbox("使用数据采样", True)
            else:
                sample_data = st.checkbox("使用数据采样", False)
        else:
            sample_data = False
            agg_method = '无'
        
    # 图表生成
    with col2:
        st.header("📊 图表展示")
        try:
            # 准备图表数据
            chart_data = st.session_state.df.copy()
            
            # 大数据处理
            if sample_data and len(chart_data) > 10000:
                chart_data = chart_data.sample(min(10000, len(chart_data)))
                st.info(f"已采样10,000行数据用于图表展示")
            
            # 时间序列图表特殊处理
            if st.session_state.chart_type == 'timeseries' and resample_freq != '原始':
                # 确保X轴是日期类型
                if pd.api.types.is_datetime64_any_dtype(chart_data[x_axis]):
                    # 设置日期为索引
                    ts_data = chart_data.set_index(x_axis)[y_axis]
                    
                    # 映射频率到Pandas偏移别名
                    freq_map = {
                        '日': 'D',
                        '周': 'W',
                        '月': 'M',
                        '季度': 'Q',
                        '年': 'Y'
                    }
                    
                    # 应用重采样
                    agg_func = {
                        '平均值': 'mean',
                        '总和': 'sum',
                        '最大值': 'max',
                        '最小值': 'min'
                    }[agg_method]
                    
                    resampled = ts_data.resample(freq_map[resample_freq]).agg(agg_func)
                    chart_data = resampled.reset_index()
                    chart_data.columns = [x_axis, y_axis]
                    st.info(f"已按{resample_freq}频率聚合数据 ({agg_method})")
            
            # 数据聚合 (非时间序列)
            if agg_method != '无' and st.session_state.chart_type in ['line', 'bar', 'area']:
                if group_col != '无':
                    agg_df = chart_data.groupby([x_axis, group_col], as_index=False).agg({
                        y_axis: 'mean' if agg_method == '平均值' else 'sum' if agg_method == '总和' else 'count'
                    })
                    chart_data = agg_df
                    st.info(f"已按{x_axis}和{group_col}分组聚合数据 ({agg_method})")
            
            # 生成图表
            if st.session_state.chart_type in ['line', 'timeseries']:
                if group_col != '无':
                    fig = px.line(chart_data, x=x_axis, y=y_axis, color=group_col, 
                                 title=chart_title, template=theme)
                else:
                    fig = px.line(chart_data, x=x_axis, y=y_axis, 
                                 title=chart_title, template=theme)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'bar':
                if group_col != '无':
                    fig = px.bar(chart_data, x=x_axis, y=y_axis, color=group_col, 
                                barmode='group', title=chart_title, template=theme)
                else:
                    fig = px.bar(chart_data, x=x_axis, y=y_axis, 
                                title=chart_title, template=theme)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'scatter':
                color_arg = color_col if color_col != '无' else None
                size_arg = size_col if size_col != '无' else None
                hover_arg = hover_data if hover_data else None
                
                fig = px.scatter(chart_data, x=x_axis, y=y_axis, 
                                color=color_arg, size=size_arg, hover_data=hover_arg,
                                title=chart_title, template=theme)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'pie':
                fig = px.pie(chart_data, names=names_col, values=values_col,
                            title=chart_title, template=theme, hole=hole_size)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'box':
                fig = px.box(chart_data, x=cat_col, y=val_col, 
                            title=chart_title, template=theme, color=cat_col)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'heatmap':
                numeric_cols = chart_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    corr = chart_data[numeric_cols].corr()
                    fig = px.imshow(corr, text_auto=annotate, aspect="auto",
                                   color_continuous_scale=color_palette,
                                   title=chart_title, template=theme)
                    fig.update_layout(height=height, width=width)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("没有找到数值列进行相关性分析")
                
            elif st.session_state.chart_type == 'area':
                if group_col != '无':
                    fig = px.area(chart_data, x=x_axis, y=y_axis, color=group_col,
                                 title=chart_title, template=theme)
                else:
                    fig = px.area(chart_data, x=x_axis, y=y_axis,
                                 title=chart_title, template=theme)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
            elif st.session_state.chart_type == 'histogram':
                if hist_group != '无':
                    fig = px.histogram(chart_data, x=hist_col, color=hist_group,
                                      nbins=bins, title=chart_title, template=theme,
                                      marginal="rug", opacity=0.7)
                else:
                    fig = px.histogram(chart_data, x=hist_col, nbins=bins,
                                      title=chart_title, template=theme)
                fig.update_layout(height=height, width=width)
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            st.error(f"生成图表时出错: {str(e)}")
            st.info("请检查选择的列是否适合图表类型")
    
    st.markdown("---")
    
    # 数据分析部分 - 优化为使用采样数据
    st.header("🔬 数据分析")
    
    # 使用采样数据进行分析
    if len(st.session_state.df) > 10000:
        analysis_data = st.session_state.df.sample(min(10000, len(st.session_state.df)))
        st.warning(f"分析使用10,000行采样数据 (原始数据: {len(st.session_state.df)}行)")
    else:
        analysis_data = st.session_state.df
    
    if st.session_state.analysis_type == 'summary':
        st.subheader("数据摘要统计")
        st.dataframe(analysis_data.describe().T)
        
        st.subheader("缺失值分析")
        missing_df = pd.DataFrame({
            '缺失值数量': analysis_data.isnull().sum(),
            '缺失值比例 (%)': (analysis_data.isnull().sum() / len(analysis_data)) * 100
        })
        st.dataframe(missing_df)
        
        # 缺失值可视化
        if missing_df['缺失值数量'].sum() > 0:
            st.subheader("缺失值分布")
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(analysis_data.isnull(), cbar=False, cmap='viridis', ax=ax)
            st.pyplot(fig)
        
    elif st.session_state.analysis_type == 'correlation':
        st.subheader("数值列相关性分析")
        numeric_cols = analysis_data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            # 相关性矩阵
            corr = analysis_data[numeric_cols].corr()
            st.dataframe(corr.style.background_gradient(cmap='coolwarm', axis=None))
            
            # 相关性热力图
            st.subheader("相关性热力图")
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
            st.pyplot(fig)
            
            # 强相关性分析
            st.subheader("强相关性分析 (|r| > 0.7)")
            strong_corrs = corr.unstack().sort_values(ascending=False)
            strong_corrs = strong_corrs[strong_corrs < 1.0]  # 移除对角线
            strong_corrs = strong_corrs[abs(strong_corrs) > 0.7]
            if len(strong_corrs) > 0:
                st.write(strong_corrs)
            else:
                st.info("没有找到强相关关系 (|r| > 0.7)")
        else:
            st.warning("没有找到数值列进行相关性分析")
            
    elif st.session_state.analysis_type == 'timeseries':
        if st.session_state.date_columns:
            date_col = st.selectbox("选择日期列", st.session_state.date_columns)
            value_col = st.selectbox("选择分析列", analysis_data.columns)
            
            if pd.api.types.is_numeric_dtype(analysis_data[value_col]):
                st.subheader("时间序列趋势")
                ts_df = analysis_data.set_index(date_col)[value_col]
                
                # 滚动平均
                window = st.slider("滚动平均窗口大小", 1, 90, 7)
                rolling_mean = ts_df.rolling(window=window).mean()
                
                fig, ax = plt.subplots(figsize=(12, 6))
                ts_df.plot(ax=ax, label='原始数据', alpha=0.5)
                rolling_mean.plot(ax=ax, label=f'{window}天滚动平均', linewidth=2)
                ax.set_title(f"{value_col} 时间序列分析")
                ax.set_xlabel("日期")
                ax.set_ylabel(value_col)
                ax.legend()
                st.pyplot(fig)
                
                # 季节性分析
                st.subheader("季节性分析")
                try:
                    import statsmodels.api as sm
                    decomposition = sm.tsa.seasonal_decompose(ts_df.dropna(), period=30)
                    
                    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 10))
                    decomposition.observed.plot(ax=ax1, title='观测值')
                    decomposition.trend.plot(ax=ax2, title='趋势')
                    decomposition.seasonal.plot(ax=ax3, title='季节性')
                    decomposition.resid.plot(ax=ax4, title='残差')
                    fig.tight_layout()
                    st.pyplot(fig)
                except ImportError:
                    st.warning("时间序列分解需要statsmodels库，请使用`pip install statsmodels`安装")
            else:
                st.warning("请选择数值列进行分析")
        else:
            st.warning("没有找到日期/时间列")
            
    elif st.session_state.analysis_type == 'categorical':
        cat_col = st.selectbox("选择分类列", analysis_data.columns)
        if len(analysis_data[cat_col].unique()) < 50:  # 避免类别过多
            st.subheader("分类统计")
            summary = analysis_data[cat_col].value_counts().reset_index()
            summary.columns = ['类别', '计数']
            summary['比例 (%)'] = (summary['计数'] / summary['计数'].sum()) * 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(summary)
            with col2:
                fig = px.pie(summary, names='类别', values='计数', 
                            title=f"{cat_col}分布")
                st.plotly_chart(fig, use_container_width=True)
            
            # 分类数值分析
            st.subheader("分类数值分析")
            num_cols = st.selectbox("选择数值列", 
                                   analysis_data.select_dtypes(include=np.number).columns.tolist())
            
            if num_cols:
                fig = px.box(analysis_data, x=cat_col, y=num_cols, 
                            title=f"{cat_col} vs {num_cols}")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("该列包含过多唯一值，不适合分类分析")
    
    # 数据导出
    st.markdown("---")
    st.header("💾 导出结果")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.subheader("导出图表")
        chart_format = st.selectbox("图表格式", ["PNG", "SVG", "PDF"])
        if st.button("导出当前图表"):
            try:
                buf = io.BytesIO()
                fig.write_image(buf, format=chart_format.lower())
                st.download_button(
                    label="下载图表",
                    data=buf.getvalue(),
                    file_name=f"chart_{datetime.now().strftime('%Y%m%d_%H%M')}.{chart_format.lower()}",
                    mime=f"image/{chart_format.lower()}"
                )
            except:
                st.error("图表导出失败，请先生成图表")
    
    with export_col2:
        st.subheader("导出数据")
        data_format = st.selectbox("数据格式", ["CSV", "Excel"])
        export_size = st.slider("导出行数", 1000, 100000, 10000, 1000)
        
        if st.button(f"导出数据 (最多{export_size}行)"):
            try:
                export_df = st.session_state.df.head(export_size)
                
                if data_format == "CSV":
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="下载CSV",
                        data=csv,
                        file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
                else:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        export_df.to_excel(writer, index=False)
                    st.download_button(
                        label="下载Excel",
                        data=excel_buffer.getvalue(),
                        file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
            except Exception as e:
                st.error(f"数据导出失败: {str(e)}")

else:
    st.info("请上传数据文件或生成示例数据")

# 页脚
st.markdown("---")
st.caption("© 2023 高级图表分析工具 | 支持多种日期/时间格式和时间序列分析")

# pip install streamlit pandas numpy matplotlib seaborn plotly openpyxl xlsxwriter
# streamlit run data_analysis.py