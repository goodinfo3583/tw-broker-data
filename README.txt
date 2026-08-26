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
│   ├── broker_ranking.json
│   ├── broker_trades_latest.json
│   ├── broker_trends.json
│   └── target_broker_trades.json 
│
├── fetch_broker_data.py #苦工小弟
├── update_broker.py     #指揮官
└── ReadMe.txt
