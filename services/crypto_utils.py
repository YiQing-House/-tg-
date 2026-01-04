"""
AES-256-CBC 文件加密工具
用于 Telegram Private Vault 的文件加密/解密

文件格式: [IV (16 bytes)] + [Encrypted Content (PKCS7 Padded)]
"""
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# AES-256-CBC 参数
BLOCK_SIZE = 16  # AES 块大小
KEY_SIZE = 32    # AES-256 密钥长度
CHUNK_SIZE = 64 * 1024  # 64KB 流式处理块大小


def generate_key():
    """生成随机 32 字节 (256位) 密钥"""
    return os.urandom(KEY_SIZE)


def encrypt_file(input_path: str, output_path: str, key: bytes) -> str:
    """
    使用 AES-256-CBC 对文件进行全量加密。
    
    Args:
        input_path: 原始文件路径
        output_path: 加密后文件保存路径
        key: 32 字节密钥
    
    Returns:
        加密后文件路径
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")
    
    # 生成随机 IV
    iv = os.urandom(BLOCK_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
        # 写入 IV (明文存储在文件头)
        f_out.write(iv)
        
        # 流式读取并加密
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            
            if len(chunk) == 0:
                # 文件读完了，需要写入一个完整的 padding 块 (当文件大小正好是 BLOCK_SIZE 倍数时)
                # pad(b'', BLOCK_SIZE) 会返回 16 字节的 padding (0x10 重复 16 次)
                final_block = pad(b'', BLOCK_SIZE)
                f_out.write(cipher.encrypt(final_block))
                break
            elif len(chunk) < CHUNK_SIZE:
                # 最后一块（不满 CHUNK_SIZE），加 padding 后加密
                padded_chunk = pad(chunk, BLOCK_SIZE)
                f_out.write(cipher.encrypt(padded_chunk))
                break
            else:
                # 满块，直接加密 (CHUNK_SIZE 是 BLOCK_SIZE 的倍数，所以没问题)
                f_out.write(cipher.encrypt(chunk))
    
    return output_path


def decrypt_file(input_path: str, output_path: str, key: bytes) -> str:
    """
    解密 AES-256-CBC 加密的文件。
    
    Args:
        input_path: 加密文件路径
        output_path: 解密后文件保存路径
        key: 32 字节密钥
    
    Returns:
        解密后文件路径
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")
    
    with open(input_path, 'rb') as f_in:
        # 读取 IV
        iv = f_in.read(BLOCK_SIZE)
        if len(iv) != BLOCK_SIZE:
            raise ValueError("File too short or corrupted (missing IV)")
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        with open(output_path, 'wb') as f_out:
            # 使用预读策略判断是否是最后一块
            prev_chunk = None
            
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                
                if prev_chunk is not None:
                    if len(chunk) == 0:
                        # prev_chunk 是最后一块，需要 unpad
                        decrypted = cipher.decrypt(prev_chunk)
                        try:
                            unpadded = unpad(decrypted, BLOCK_SIZE)
                            f_out.write(unpadded)
                        except ValueError as e:
                            raise ValueError(f"Decryption failed: {e}")
                        break
                    else:
                        # prev_chunk 不是最后一块，直接写入
                        decrypted = cipher.decrypt(prev_chunk)
                        f_out.write(decrypted)
                
                if len(chunk) == 0:
                    break
                    
                prev_chunk = chunk
    
    return output_path
