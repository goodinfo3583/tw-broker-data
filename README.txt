broker_crawler/
├── .github/
│   └── workflows/
│       └── crawler.yml
│
├── data/
│   ├── broker
│   │   ├── broker_history.csv #存取每日資料堆疊
│   │   └── broker_trades.csv  #每天一份當日csv
│   ├── tpex_flows #讀取來源
│   └── twse_flows #讀取來源
│
├──docs/data
│   ├── broker_ranking.json #今日券商總排行榜
│   ├── broker_trades_latest.json #今日交易明細_前端版
│   ├── broker_trends.json #鎖定特定券商
│   └── target_broker_trades.json #歷史趨勢圖
│
├── fetch_broker_data.py #苦工小弟
├── update_broker.py     #指揮官
└── ReadMe.txt
