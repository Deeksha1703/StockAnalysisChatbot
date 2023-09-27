import json
import openai 
import pandas as pd 
import matplotlib.pyplot as plt 
import streamlit as st 
import yfinance as yf
import base64

# Read API key
try:
    openai.api_key = open('API_KEY','r').read()
except Exception as e:
    st.error(f"Error reading the API key: {e}")

def get_stock_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period='1y')
        if data.empty:
            return "No data available for the given ticker symbol."
        return str(data.iloc[-1].Close)
    except Exception as e:
        return f"An error occurred: {e}"

def calculate_SMA(ticker, window):
    try:
        data = yf.Ticker(ticker).history(period='1y').Close
        return str(data.rolling(window=window).mean().iloc[-1])
    except Exception as e:
        return f"An error occurred: {e}"

def calculate_EMA(ticker, window):
    try:
        data = yf.Ticker(ticker).history(period='1y').Close
        return str(data.ewm(span=window,adjust=False).mean().iloc[-1])
    except Exception as e:
        return f"An error occurred: {e}"

def calculate_RSI(ticker):
    try:
        data = yf.Ticker(ticker).history(period='1y').Close
        delta = data.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=14-1,adjust=False).mean()
        ema_down = down.ewm(com=14-1,adjust=False).mean()
        rs = ema_up / ema_down
        return str(100 - (100 / (1 + rs)).iloc[-1])
    except Exception as e:
        return f"An error occurred: {e}"

def calculate_MACD(ticker):
    try:
        data = yf.Ticker(ticker).history(period='1y').Close
        short_EMA = data.ewm(span=12, adjust=False).mean()
        long_EMA = data.ewm(span=26, adjust=False).mean()

        MACD = short_EMA - long_EMA
        signal = MACD.ewm(span=9, adjust=False).mean()
        MACD_histogram = MACD - signal

        return f'{MACD[-1]}, {signal[-1]}, {MACD_histogram[-1]}'
    except Exception as e:
        return f"An error occurred: {e}"

# Parameters for openai to use the functions set
# Warning: new name stocks (i.e., meta instead of fb) may not be found
functions = [
    {
        'name': 'get_stock_price',
        'description': 'Gets the latest stock price given the ticker symbol of a company.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {
                    'type': 'string',
                    'description': 'The stock ticker symbol for a company (for example AAPL for Apple). Note: FB is renamed to META'
                }
            },
            'required': ['ticker']
        },
    },
    {
        "name": "calculate_SMA",
        "description": "Calculate the simple moving average for a given stock ticker and a window.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol for a company (e.g., AAPL for Apple)",
                },
                "window": {
                    "type": "integer",
                    "description": "The timeframe to consider when calculating the SMA"
                }
            },
            "required": ["ticker", "window"]
        },
    },
    {
        "name": "calculate_EMA",
        "description": "Calculate the exponential moving average for a given stock ticker and a window.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol for a company (e.g., AAPL for Apple)",
                },
                "window": {
                    "type": "integer",
                    "description": "The timeframe to consider when calculating the EMA"
                }
            },
            "required": ["ticker", "window"]
        },
    },
    {
        "name": "calculate_RSI",
        "description": "Calculate the RSI for a given stock ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol for a company (e.g., AAPL for Apple)",
                }
            },
            "required": ["ticker"]
        },
    },
    {
        "name": "calculate_MACD",
        "description": "Calculate the MACD for a given stock ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol for a company (e.g., AAPL for Apple)",
                }
            },
            "required": ["ticker"]
        },
    },
]

available_functions={
    'get_stock_price': get_stock_price,
    'calculate_SMA': calculate_SMA,
    'calculate_EMA': calculate_EMA,
    'calculate_RSI': calculate_RSI,
    'calculate_MACD': calculate_MACD
}

# Creates Streamlit site
st.set_page_config(page_title='Stock Analysis Chatbot', initial_sidebar_state='auto')
if 'messages' not in st.session_state:
    st.session_state['messages']=[]

st.title('')  # Add an empty title to create some space
st.markdown("<h1 style='text-align: center;'>Stock Analysis Chatbot</h1>", unsafe_allow_html=True)  # Center-aligned title

# Set background color to black and text color to white
st.markdown(
    """
    <style>
    body {
        background-color: black;
        color: white;
    }
    .stApp {
        background-size: cover;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# List of topics the chatbot can answer
chatbot_topics = [
    "Stock Prices",
    "Simple Moving Averages (SMA)",
    "Exponential Moving Averages (EMA)",
    "Relative Strength Index (RSI)",
    "Moving Average Convergence Divergence (MACD)",
]

# Define the desired font size (you can adjust this as needed)
font_size = "14px"

# Adjust the margin and padding to reduce spacing
st.markdown("<style>h3 { margin-bottom: 0px; }</style>", unsafe_allow_html=True)
st.markdown("<style>ul { margin-top: 0px; padding-top: 0px; }</style>", unsafe_allow_html=True)

# Display the list of topics at the beginning of the page without bullet points and with fixed font size
st.markdown(f"<h3 style='font-size: {font_size}'>The Chatbot Can Answer Questions About:</h3>", unsafe_allow_html=True)
st.markdown("<ul style='list-style-type:none;'>", unsafe_allow_html=True)
for topic in chatbot_topics:
    st.markdown(f"<li style='font-size: {font_size}'>{topic}</li>", unsafe_allow_html=True)
st.markdown("</ul>", unsafe_allow_html=True)

user_input = st.text_input("Your Query: (e.g. What is the stock price of Microsoft?)")


if user_input:  # For when someone types something
    try:
        st.session_state['messages'].append({'role': 'user', 'content': f'{user_input}'})
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo-0613',
            messages=st.session_state['messages'],
            functions=functions,
            function_call='auto'
        )

        response_message = response['choices'][0]['message']

        if response_message.get('function_call'):
            function_name = response_message['function_call']['name']
            function_args = json.loads(response_message['function_call']['arguments'])
            if function_name in ['get_stock_price', 'calculate_RSI', 'calculate_MACD']:
                args_dict = {'ticker': function_args.get('ticker')}
            elif function_name in ['calculate_SMA', 'calculate_EMA']:
                args_dict = {'ticker': function_args.get('ticker'), 'window': function_args.get('window')}

            function_to_call = available_functions[function_name]
            function_response = function_to_call(**args_dict)

            st.session_state['messages'].append(response_message)
            st.session_state['messages'].append(
                {
                    'role': 'function',
                    'name': function_name,
                    'content': function_response
                }
            )
            second_response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo-0613',
                messages=st.session_state['messages']
            )

            assistant_response = second_response['choices'][0]['message']['content']
            st.markdown(
                f'<div class="assistant-response">{assistant_response}</div>',
                unsafe_allow_html=True
            )
            st.session_state['messages'].append({'role': 'assistant', 'content': assistant_response})

            st.markdown(# marks answer with background color
                """
                <style>
                .assistant-response {
                    background-color: #black; /* Change to the desired background color */
                    padding: 10px;
                    border-radius: 5px;
                    word-wrap: break-word;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
        else:
            st.text(response_message['content'])
            st.session_state['messages'].append({'role': 'assistant', 'content': response_message['content']})
    except Exception as e:
        st.text('Error occurred, ' + str(e))
