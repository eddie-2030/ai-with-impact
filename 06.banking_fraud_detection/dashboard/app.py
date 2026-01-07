# dashboard/app.py
import streamlit as st
import requests
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Banking Fraud Detection", layout="wide")

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

def main():
    st.title("🏦 Banking Fraud Detection System")
    st.markdown("Multi-Agent AI System for Real-Time Fraud Detection")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Process Transaction", "View Alerts", "Transaction Details", "Dashboard"])
    
    with tab1:
        st.header("Process Transaction")
        
        col1, col2 = st.columns(2)
        
        with col1:
            user_id = st.text_input("User ID", value="user-123")
            amount = st.number_input("Amount ($)", min_value=0.01, value=100.00, step=0.01)
            merchant = st.text_input("Merchant", value="Online Store")
            merchant_category = st.selectbox("Merchant Category", 
                ["retail", "restaurant", "gas_station", "online", "atm", "other"])
        
        with col2:
            location = st.text_input("Location", value="New York, NY")
            device_id = st.text_input("Device ID", value="device-456")
            transaction_type = st.selectbox("Transaction Type", 
                ["purchase", "withdrawal", "transfer", "deposit"])
            payment_method = st.selectbox("Payment Method", 
                ["card", "bank_transfer", "digital_wallet"])
        
        if st.button("Process Transaction", type="primary"):
            payload = {
                "user_id": user_id,
                "amount": amount,
                "merchant": merchant,
                "merchant_category": merchant_category,
                "location": location,
                "device_id": device_id,
                "transaction_type": transaction_type,
                "payment_method": payment_method,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                with st.spinner("Processing transaction through fraud detection agents..."):
                    response = requests.post(f"{API_URL}/transactions", json=payload, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                
                st.success("Transaction processed!")
                st.session_state['last_transaction'] = result
                
                # Display results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Risk Score", f"{result.get('risk_score', 0):.1f}/100")
                with col2:
                    st.metric("Risk Level", result.get('risk_level', 'unknown').upper())
                with col3:
                    status_color = {
                        "approved": "🟢",
                        "review": "🟡",
                        "flagged": "🔴"
                    }
                    st.metric("Status", f"{status_color.get(result.get('status', 'unknown'), '⚪')} {result.get('status', 'unknown').upper()}")
                
                # Patterns detected
                if result.get('patterns_detected'):
                    st.subheader("Detected Patterns")
                    for pattern in result['patterns_detected']:
                        st.write(f"• {pattern.replace('_', ' ').title()}")
                
                # Alert information
                if result.get('alert'):
                    st.subheader("🚨 Fraud Alert Generated")
                    alert = result['alert']
                    st.warning(f"**Severity:** {alert.get('severity', 'unknown').upper()}")
                    st.write(f"**Alert Type:** {alert.get('alert_type', 'unknown').replace('_', ' ').title()}")
                    st.write(f"**Description:** {alert.get('description', 'No description')}")
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error calling API: {str(e)}")
                st.info("Make sure the API server is running at the specified URL")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with tab2:
        st.header("Fraud Alerts")
        
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox("Filter by Status", 
                ["all", "open", "investigating", "resolved", "false_positive"])
        with col2:
            filter_severity = st.selectbox("Filter by Severity",
                ["all", "low", "medium", "high", "critical"])
        
        if st.button("Load Alerts") or True:
            try:
                params = {}
                if filter_status != "all":
                    params["status"] = filter_status
                if filter_severity != "all":
                    params["severity"] = filter_severity
                
                response = requests.get(f"{API_URL}/alerts", params=params, timeout=30)
                response.raise_for_status()
                alerts = response.json()
                
                if alerts:
                    st.success(f"Found {len(alerts)} alerts")
                    
                    # Display alerts in a table
                    df = pd.DataFrame(alerts)
                    st.dataframe(df, use_container_width=True)
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Alerts", len(alerts))
                    with col2:
                        critical_count = sum(1 for a in alerts if a.get('severity') == 'critical')
                        st.metric("Critical", critical_count)
                    with col3:
                        high_count = sum(1 for a in alerts if a.get('severity') == 'high')
                        st.metric("High", high_count)
                    with col4:
                        open_count = sum(1 for a in alerts if a.get('status') == 'open')
                        st.metric("Open", open_count)
                else:
                    st.info("No alerts found")
            except requests.exceptions.RequestException as e:
                st.error(f"Error loading alerts: {str(e)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("Transaction Details")
        
        transaction_id = st.text_input("Transaction ID", placeholder="Enter transaction ID")
        
        if st.button("Load Transaction") and transaction_id:
            try:
                response = requests.get(f"{API_URL}/transactions/{transaction_id}", timeout=30)
                response.raise_for_status()
                result = response.json()
                
                st.success("Transaction loaded!")
                
                # Transaction details
                st.subheader("Transaction Information")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Transaction ID:** {result.get('transaction_id')}")
                    st.write(f"**User ID:** {result.get('user_id')}")
                    st.write(f"**Amount:** ${result.get('amount', 0):.2f}")
                    st.write(f"**Merchant:** {result.get('merchant', 'Unknown')}")
                with col2:
                    st.write(f"**Location:** {result.get('location', 'Unknown')}")
                    st.write(f"**Status:** {result.get('status', 'unknown')}")
                    st.write(f"**Timestamp:** {result.get('timestamp', 'Unknown')}")
                
                # Risk assessment
                if result.get('risk_assessment'):
                    st.subheader("Risk Assessment")
                    risk = result['risk_assessment']
                    st.metric("Risk Score", f"{risk.get('risk_score', 0):.1f}/100")
                    st.metric("Risk Level", risk.get('risk_level', 'unknown').upper())
                    if risk.get('analysis'):
                        st.write("**Analysis:**")
                        st.write(risk['analysis'])
                
                # Alerts
                if result.get('alerts'):
                    st.subheader("Fraud Alerts")
                    for alert in result['alerts']:
                        with st.expander(f"Alert: {alert.get('alert_type', 'Unknown')} - {alert.get('severity', 'unknown').upper()}"):
                            st.write(f"**Alert ID:** {alert.get('alert_id')}")
                            st.write(f"**Status:** {alert.get('status', 'unknown')}")
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error loading transaction: {str(e)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        # Show last transaction if available
        if 'last_transaction' in st.session_state:
            st.divider()
            st.subheader("Last Processed Transaction")
            if st.button("View Last Transaction"):
                st.json(st.session_state['last_transaction'])
    
    with tab4:
        st.header("Fraud Detection Dashboard")
        st.info("Dashboard analytics coming soon! This will show fraud trends, patterns, and statistics.")

if __name__ == "__main__":
    main()

