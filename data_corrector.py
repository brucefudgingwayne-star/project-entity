import pandas as pd
import numpy as np

def validate_and_clean_crypto_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a raw crypto historical dataframe, fixes missing values, 
    removes duplicates, handles infinities, and interpolates data gaps.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # Ensure standard column names
    df.columns = [col.lower().strip() for col in df.columns]

    # Map common variations to standard names
    rename_map = {
        'time': 'timestamp', 'date': 'timestamp', 'dt': 'timestamp',
        'open_price': 'open', 'high_price': 'high', 
        'low_price': 'low', 'close_price': 'close', 'vol': 'volume'
    }
    df = df.rename(columns=rename_map)

    # Required core columns for quant calculations
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns and col != 'timestamp':
            df[col] = 0.0  # Fallback if a column is missing

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp')
        df = df.drop_duplicates(subset=['timestamp'])
        df.set_index('timestamp', inplace=True)

    # Convert numeric columns safely, coercing errors to NaN
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Handle missing history (shredded data gaps) via linear interpolation
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].interpolate(method='linear')

    # Forward fill any remaining edge NaNs, then backward fill
    df = df.ffill().bfill()

    # Replace any infinities or extreme outliers
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.dropna()

    return df.reset_index()