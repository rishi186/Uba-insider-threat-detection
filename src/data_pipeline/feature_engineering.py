"""
Behavioral Feature Engineering for UBA & ITD.

Produces daily per-user features including:
  - FAR: File Access Ratio (user vs peer-group)
  - EDS: Email Deviation Score (z-score vs peers)
  - IAV: Inactive Activity Variance
  - OAF: Odd Activity Fraction (after-hours ratio)
  - Login Entropy
  - file_count, email_count
  
  ** Threat-Discriminating Features (new) **
  - file_copy_count: number of File Copy events
  - usb_events: number of USB Connect events
  - to_removable_count: files sent to removable media
  - confidential_file_count: files with CONFIDENTIAL in name
  - after_hours_event_count: raw count of after-hours events
"""

import pandas as pd
import numpy as np
from scipy.stats import entropy
import os
import sys
import logging

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.config import config

logger = logging.getLogger("uba.data_pipeline.feature_engineering")

# Config-driven work-hour definition
_features_cfg = config.get('features', {})
WORK_START_HOUR = _features_cfg.get('work_start_hour', 7)
WORK_END_HOUR = _features_cfg.get('work_end_hour', 20)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
RAW_DIR = os.path.join(PROJECT_ROOT, "data/raw")


class BehavioralFeatureEngine:
    def __init__(self, users_df_path):
        self.users_df = pd.read_csv(users_df_path)
        if 'id' in self.users_df.columns:
            self.users_df.rename(columns={'id': 'user'}, inplace=True)
        self.role_map = self.users_df.set_index('user')['role'].to_dict()
        
        # Load raw event data for threat-discriminating features
        self.raw_file_df = None
        self.raw_device_df = None
        self._load_raw_data()
    
    def _load_raw_data(self):
        """Load raw CSVs to extract threat-level signals."""
        file_path = os.path.join(RAW_DIR, "file.csv")
        device_path = os.path.join(RAW_DIR, "device.csv")
        
        if os.path.exists(file_path):
            self.raw_file_df = pd.read_csv(file_path)
            self.raw_file_df['date'] = pd.to_datetime(self.raw_file_df['date'])
            self.raw_file_df['day'] = self.raw_file_df['date'].dt.date
            logger.info("Loaded raw file events: %d rows", len(self.raw_file_df))
        
        if os.path.exists(device_path):
            self.raw_device_df = pd.read_csv(device_path)
            self.raw_device_df['date'] = pd.to_datetime(self.raw_device_df['date'])
            self.raw_device_df['day'] = self.raw_device_df['date'].dt.date
            logger.info("Loaded raw device events: %d rows", len(self.raw_device_df))
    
    def _get_threat_features(self, user, day):
        """Extract threat-discriminating features for a user-day from raw data."""
        result = {
            'file_copy_count': 0,
            'usb_events': 0,
            'to_removable_count': 0,
            'confidential_file_count': 0,
        }
        
        # File-level threat signals
        if self.raw_file_df is not None:
            user_day_files = self.raw_file_df[
                (self.raw_file_df['user'] == user) & 
                (self.raw_file_df['day'] == day)
            ]
            
            if not user_day_files.empty:
                # File Copy count
                if 'activity' in user_day_files.columns:
                    result['file_copy_count'] = int(
                        (user_day_files['activity'] == 'File Copy').sum()
                    )
                
                # Removable media
                if 'to_removable_media' in user_day_files.columns:
                    result['to_removable_count'] = int(
                        user_day_files['to_removable_media'].sum()
                    )
                
                # Confidential files
                if 'filename' in user_day_files.columns:
                    result['confidential_file_count'] = int(
                        user_day_files['filename'].str.contains(
                            'CONFIDENTIAL', case=False, na=False
                        ).sum()
                    )
        
        # Device/USB signals
        if self.raw_device_df is not None:
            user_day_devices = self.raw_device_df[
                (self.raw_device_df['user'] == user) & 
                (self.raw_device_df['day'] == day)
            ]
            result['usb_events'] = len(user_day_devices)
        
        return result
        
    def calculate_features(self, df):
        logger.info("Calculating behavioral features...")
        
        # Ensure datetime
        df['date'] = pd.to_datetime(df['date'])
        df['hour'] = df['date'].dt.hour
        df['day'] = df['date'].dt.date
        
        daily_stats = []
        
        for user, group in df.groupby('user'):
            role = self.role_map.get(user, 'Unknown')
            
            for day, day_data in group.groupby('day'):
                day_data = day_data.sort_values('date')
                
                # --- Basic Counts ---
                file_count = len(day_data[day_data['source'] == 'File'])
                email_count = len(day_data[day_data['source'] == 'Email'])
                
                # --- IAV (Inactive Activity Variance) ---
                time_deltas = day_data['date'].diff().dt.total_seconds().dropna()
                if len(time_deltas) > 1:
                    iav = time_deltas.var()
                else:
                    iav = 0
                
                # --- OAF (Odd Activity Fraction) ---
                odd_hours = day_data[
                    (day_data['hour'] < WORK_START_HOUR) | 
                    (day_data['hour'] > WORK_END_HOUR)
                ]
                oaf = len(odd_hours) / len(day_data) if len(day_data) > 0 else 0
                after_hours_event_count = len(odd_hours)
                
                # --- Login Entropy ---
                hour_counts = day_data['hour'].value_counts()
                login_entropy = entropy(hour_counts) if len(hour_counts) > 1 else 0
                
                # --- Threat-Discriminating Features ---
                threat_feats = self._get_threat_features(user, day)
                
                daily_stats.append({
                    'user': user,
                    'role': role,
                    'day': day,
                    'file_count': file_count,
                    'email_count': email_count,
                    'iav': iav,
                    'oaf': oaf,
                    'after_hours_event_count': after_hours_event_count,
                    'login_entropy': login_entropy,
                    **threat_feats,
                })
        
        features_df = pd.DataFrame(daily_stats)
        
        # Peer Group Stats (FAR & EDS)
        logger.info("Calculating Peer Group Statistics...")
        
        peer_stats = features_df.groupby(['role', 'day']).agg({
            'file_count': 'mean',
            'email_count': ['mean', 'std']
        }).reset_index()
        
        peer_stats.columns = ['role', 'day', 'peer_file_mean', 'peer_email_mean', 'peer_email_std']
        
        features_df = pd.merge(features_df, peer_stats, on=['role', 'day'], how='left')
        
        # FAR
        features_df['far'] = features_df['file_count'] / (features_df['peer_file_mean'] + 1e-6)
        
        # EDS
        features_df['eds'] = (features_df['email_count'] - features_df['peer_email_mean']) / (features_df['peer_email_std'] + 1e-6)
        
        # Fill NaN
        features_df = features_df.fillna(0)
        
        # Select final columns (including new threat-discriminating features)
        final_df = features_df[[
            'user', 'role', 'day',
            'far', 'eds', 'iav', 'oaf', 'login_entropy',
            'file_count', 'email_count',
            'file_copy_count', 'usb_events', 'to_removable_count',
            'confidential_file_count', 'after_hours_event_count',
        ]]
        
        # Log threat user summary
        threat_user = config.get('data_generation', {}).get('insider_threat_user', 'U105')
        threat_data = final_df[final_df['user'] == threat_user]
        if not threat_data.empty:
            logger.info("Threat user %s feature summary:", threat_user)
            logger.info("  file_copy_count: total=%d, max/day=%d",
                        threat_data['file_copy_count'].sum(),
                        threat_data['file_copy_count'].max())
            logger.info("  to_removable_count: total=%d", threat_data['to_removable_count'].sum())
            logger.info("  confidential_file_count: total=%d", threat_data['confidential_file_count'].sum())
            logger.info("  usb_events: total=%d", threat_data['usb_events'].sum())
        
        return final_df


def run_feature_engineering(input_path=None, output_path=None):
    """Entry point for feature engineering, callable from run_all.py."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
    
    if input_path is None:
        input_path = os.path.join(PROJECT_ROOT, "data/processed/master_timeline.parquet")
    if output_path is None:
        output_path = os.path.join(PROJECT_ROOT, "data/processed/featured_timeline.parquet")
    
    USERS_PATH = os.path.join(PROJECT_ROOT, "data/raw/users.csv")
    
    if os.path.exists(input_path):
        df = pd.read_parquet(input_path)
        engine = BehavioralFeatureEngine(USERS_PATH)
        features = engine.calculate_features(df)
        
        # Save both formats
        csv_path = output_path.replace('.parquet', '.csv')
        features.to_csv(csv_path, index=False)
        features.to_parquet(output_path, index=False)
        logger.info("Features saved to %s and %s", csv_path, output_path)
        logger.info("\n%s", features.head())
    else:
        logger.error("Master timeline not found at %s", input_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_feature_engineering()
