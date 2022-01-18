#pip install -U kaleido
#pip install plotly

from plotly.subplots import make_subplots
import plotly.graph_objects as go
from plotly.offline import init_notebook_mode, plot_mpl
import plotly.express as px
import pandas as pd
import pandas as pd
from sqlalchemy import create_engine

def showdata(lineid):
    # 初始化資料庫連線，使用pymysql模組
    # MySQL的使用者：tfi101, 密碼:123456, 埠：3306,資料庫：mydb
    engine = create_engine('mysql+pymysql://root:123456@52.193.42.101:3306/healthrobot')
    # 查詢語句，選出employee表中的所有資料
    # lineid = "'ytw00QqxJ3o3KMGUwyE7fF5WFnbxtz4H'" #輸入對向的lineid
    sql = '''
    select *,count(d.recordtime) from (select * from healthinfo where lineid ={id} order by recordtime) d group by d.recordtime order by d.recordtime
    '''.format(id=lineid)
    print(sql)
    # read_sql_query的兩個引數: sql語句， 資料庫連線
    df = pd.read_sql_query(sql, engine)
    return df

def drawpic(lineid, messageid):
    #範圍設定
    df = showdata(lineid)
    if max(df['bp_high']) > 140:
        y_maxhigh=max(df['bp_high'])+10
    else:
        y_maxhigh=150

    if min(df['bp_high']) < 100:
        y_minhigh=min(df['bp_high'])-10
    else:
        y_minhigh=50

    if max(df['bp_low']) > 90:
        y_maxlow=max(df['bp_low'])+10
    else:
        y_maxlow=110
        
    if max(df['bs']) > 100:
        y_maxbs=max(df['bs'])+10
    else:
        y_maxbs=120

    #建立圖表數
    fig = make_subplots(rows=1, cols=3,
                    subplot_titles=("bpHigh", "bpLow","bs"))

    #建立圖表
    fig.add_trace(go.Scatter(x = df['recordtime'],
                            y = df['bp_high'],
                            mode = 'lines+markers',
                            name = 'bp_high'),
                row=1,col=1)
    fig.add_hline(y=100, line_color = 'red',row=1,col=1)
    fig.add_hline(y=140, line_color = 'red',row=1,col=1)
    fig.add_hrect(y0=100, y1=y_minhigh, line_width=0, fillcolor="red", opacity=0.1, row=1,col=1)
    fig.add_hrect(y0=140, y1=y_maxhigh, line_width=0, fillcolor="red", opacity=0.1, row=1,col=1)

    fig.add_trace(go.Scatter(x = df['recordtime'],
                            y = df['bp_low'],
                            mode = 'lines+markers',
                            name = 'bp Low'),
                row=1,col=2)
    fig.add_hline(y=90, line_color ='red',row=1,col=2)
    fig.add_hrect(y0=90, y1=y_maxlow, line_width=0, fillcolor="red", opacity=0.1,row=1,col=2)

    fig.add_trace(go.Scatter(x = df['recordtime'],
                            y = df['bs'],
                            mode = 'lines+markers',
                            name = 'bs'),
                row=1,col=3)  
    fig.add_hline(y=100, line_color ='red', row=1,col=3)
    fig.add_hrect(y0=100, y1=y_maxbs, line_width=0, fillcolor="red", opacity=0.1, row=1,col=3)

    #輸出圖表
    fig.update_layout(height=400, width=900, title_text="William")    
    #轉成PNG圖檔
    path= './static/'+ messageid +'.png'
    fig.write_image(path)     
    return path


