#!/bin/bash
#!/bin/bash
python src/run_monitor.py &
streamlit run src/main.py --server.port 8080 --server.headless true
