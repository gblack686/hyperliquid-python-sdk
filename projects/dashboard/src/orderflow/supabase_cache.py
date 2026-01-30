"""
Supabase Cache Manager for Order Flow Data
Provides persistent caching of API responses and processed data
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
import pandas as pd
from loguru import logger
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseCache:
    """Manages caching of order flow data in Supabase"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found - caching disabled")
            self.client = None
        else:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            self._ensure_cache_table()
    
    def _ensure_cache_table(self):
        """Ensure cache table exists in Supabase"""
        try:
            # Check if table exists by trying to query it
            self.client.table('orderflow_cache').select('cache_key').limit(1).execute()
        except Exception as e:
            logger.info(f"Cache table might not exist: {e}")
            # Table creation should be done via Supabase dashboard or migration
            # For now, we'll just log the issue
    
    def _generate_cache_key(self, key_type: str, **params) -> str:
        """Generate a unique cache key based on parameters"""
        # Sort params for consistent hashing
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params)
        
        # Create hash of parameters
        hash_obj = hashlib.md5(f"{key_type}:{param_str}".encode())
        return hash_obj.hexdigest()
    
    def get(self, key_type: str, **params) -> Optional[Any]:
        """Get cached data from Supabase"""
        if not self.client:
            return None
        
        cache_key = self._generate_cache_key(key_type, **params)
        
        try:
            # Query cache table
            response = self.client.table('orderflow_cache').select('*').eq(
                'cache_key', cache_key
            ).execute()
            
            if response.data and len(response.data) > 0:
                cached_item = response.data[0]
                
                # Check if cache is still valid
                expires_at = datetime.fromisoformat(cached_item['expires_at'].replace('Z', '+00:00'))
                if expires_at > datetime.now(timezone.utc):
                    logger.debug(f"Cache hit for {key_type}")
                    
                    # Deserialize data based on type
                    data = json.loads(cached_item['data'])
                    
                    # Convert back to DataFrame if needed
                    if cached_item.get('data_type') == 'dataframe':
                        return pd.DataFrame(data)
                    
                    return data
                else:
                    logger.debug(f"Cache expired for {key_type}")
                    # Delete expired cache
                    self.client.table('orderflow_cache').delete().eq(
                        'cache_key', cache_key
                    ).execute()
            
        except Exception as e:
            logger.error(f"Error retrieving cache: {e}")
        
        return None
    
    def set(self, key_type: str, data: Any, ttl_minutes: int = 5, **params):
        """Set cache data in Supabase"""
        if not self.client:
            return
        
        cache_key = self._generate_cache_key(key_type, **params)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        
        try:
            # Serialize data
            data_type = 'json'
            if isinstance(data, pd.DataFrame):
                data_type = 'dataframe'
                serialized_data = data.to_json(orient='records', date_format='iso')
            else:
                serialized_data = json.dumps(data, default=str)
            
            # Prepare cache record
            cache_record = {
                'cache_key': cache_key,
                'key_type': key_type,
                'data': serialized_data,
                'data_type': data_type,
                'expires_at': expires_at.isoformat(),
                'params': json.dumps(params),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert cache (insert or update)
            self.client.table('orderflow_cache').upsert(
                cache_record,
                on_conflict='cache_key'
            ).execute()
            
            logger.debug(f"Cache set for {key_type}, expires in {ttl_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
    
    def clear_all(self):
        """Clear all cache entries"""
        if not self.client:
            return
        
        try:
            self.client.table('orderflow_cache').delete().neq('cache_key', '').execute()
            logger.info("All cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def clear_by_type(self, key_type: str):
        """Clear cache entries by type"""
        if not self.client:
            return
        
        try:
            self.client.table('orderflow_cache').delete().eq('key_type', key_type).execute()
            logger.info(f"Cache cleared for type: {key_type}")
        except Exception as e:
            logger.error(f"Error clearing cache by type: {e}")
    
    def clear_expired(self):
        """Clear expired cache entries"""
        if not self.client:
            return
        
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            self.client.table('orderflow_cache').delete().lt('expires_at', current_time).execute()
            logger.info("Expired cache entries cleared")
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")

# Global cache instance
cache = SupabaseCache()