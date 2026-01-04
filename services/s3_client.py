import boto3
import os
from config import S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, S3_PUBLIC_DOMAIN

class S3Storage:
    def __init__(self):
        self.endpoint = S3_ENDPOINT_URL
        self.access_key = S3_ACCESS_KEY
        self.secret_key = S3_SECRET_KEY
        self.bucket = S3_BUCKET_NAME
        self.public_domain = S3_PUBLIC_DOMAIN
        
        # 只有在配置了 endpoint 时才初始化
        if self.endpoint and self.access_key:
            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
        else:
            self.client = None

    def upload_file(self, file_path, object_name=None):
        """上传文件到 S3"""
        if not self.client:
            raise Exception("S3 client not configured")
        
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            self.client.upload_file(file_path, self.bucket, object_name)
            return object_name
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            return None

    def generate_presigned_url(self, object_name, expiration=3600):
        """生成预签名下载链接"""
        if not self.client:
            return None
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_name},
                ExpiresIn=expiration
            )
            
            # 如果配置了自定义域名，替换掉默认的 S3 域名
            if self.public_domain:
                # 假设 S3 URL 格式是 https://endpoint/bucket/key 或 https://bucket.endpoint/key
                # 这里的替换逻辑比较简单，生产环境可能需要更严谨的 URL构建
                # R2 的话预签名 URL 通常包含签名参数，直接替换域名可能导致签名失败
                # 对于 R2 + Cloudflare CDN，应该直接用 public_domain + key (如果公开访问)
                # 如果是私有 bucket，必须用带签名的原始 URL
                pass 
                
            return url
        except Exception as e:
            print(f"S3 Presign Error: {e}")
            return None

# 全局实例
s3 = S3Storage()
