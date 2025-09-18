from fastapi import APIRouter, Query, Body
from fastapi.responses import JSONResponse
import os

PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config_prompts')
router = APIRouter()

@router.get('/prompts/list')
def list_prompts():
    files = [f for f in os.listdir(PROMPT_DIR) if os.path.isfile(os.path.join(PROMPT_DIR, f))]
    return {'files': files}

@router.get('/list')
def list_prompts_noapi():
    return list_prompts()

@router.get('/prompts/file')
def get_prompt_file(name: str = Query(...)):
    file_path = os.path.join(PROMPT_DIR, name)
    if not os.path.isfile(file_path):
        return JSONResponse(status_code=404, content={'error': 'File not found'})
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return {'name': name, 'content': content}

@router.get('/file')
def get_prompt_file_noapi(name: str = Query(...)):
    return get_prompt_file(name)

@router.post('/prompts/file')
def save_prompt_file(name: str = Body(...), content: str = Body(...)):
    file_path = os.path.join(PROMPT_DIR, name)
    
    # If file exists, create a backup (support Chinese and English suffixes)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            # Create backup file name (fixed format, overwrite old backup)
            backup_name = f"{name}_backup"
            backup_path = os.path.join(PROMPT_DIR, backup_name)
            
            # 如果备份文件已存在，先删除
            if os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"[save_prompt_file] 删除旧备份: {backup_name}", flush=True)
            
            # Create new backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(old_content)
            print(f"[save_prompt_file] create backup: {backup_name}", flush=True)
        except Exception as e:
            print(f"[save_prompt_file] create backup failed: {str(e)}", flush=True)
    
    # Save new content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'status': 'success', 'name': name}

@router.post('/file')
def save_prompt_file_noapi(name: str = Body(...), content: str = Body(...)):
    return save_prompt_file(name, content)

@router.post('/prompts/new')
def new_prompt_file(name: str = Body(...), content: str = Body(...)):
    file_path = os.path.join(PROMPT_DIR, name)
    if os.path.exists(file_path):
        return JSONResponse(status_code=409, content={'error': 'File already exists'})
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'status': 'created', 'name': name}

@router.post('/new')
def new_prompt_file_noapi(name: str = Body(...), content: str = Body(...)):
    return new_prompt_file(name, content)

@router.post('/prompts/delete')
def delete_prompt_file(request: dict = Body(...)):
    print(f"[delete_prompt_file] received delete request: {request}", flush=True)
    
    # 从请求体中提取文件名
    name = request.get('name')
    if not name:
        print(f"[delete_prompt_file] missing 'name' in body", flush=True)
        return JSONResponse(status_code=422, content={'error': 'Missing name field in request body'})
    
    print(f"[delete_prompt_file] file name: {name}", flush=True)
    
    # 添加文件名验证
    if not name.strip():
        print(f"[delete_prompt_file] empty file name", flush=True)
        return JSONResponse(status_code=422, content={'error': 'File name cannot be empty'})
    
    # 检查文件名是否包含非法字符
    import re
    if re.search(r'[<>:"/\\|?*]', name):
        print(f"[delete_prompt_file] invalid chars in name: {name}", flush=True)
        return JSONResponse(status_code=422, content={'error': 'File name contains invalid characters'})
    
    file_path = os.path.join(PROMPT_DIR, name)
    print(f"[delete_prompt_file] file path: {file_path}", flush=True)
    print(f"[delete_prompt_file] exists: {os.path.isfile(file_path)}", flush=True)
    
    if not os.path.isfile(file_path):
        print(f"[delete_prompt_file] file not found: {file_path}", flush=True)
        return JSONResponse(status_code=404, content={'error': 'File not found'})
    
    try:
        # 读取文件内容用于备份
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup file name (fixed format, overwrite old backup)
        backup_name = f"{name}_delete_backup"
        backup_path = os.path.join(PROMPT_DIR, backup_name)
        
        # 如果备份文件已存在，先删除
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"[delete_prompt_file] 删除旧备份: {backup_name}", flush=True)
        
        # 创建新备份
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[delete_prompt_file] 创建备份: {backup_name}", flush=True)
        
        # Delete source file
        os.remove(file_path)
        print(f"[delete_prompt_file] deleted: {name}", flush=True)
        return {'status': 'deleted', 'name': name, 'backup': backup_name}
    except Exception as e:
        print(f"[delete_prompt_file] delete failed: {str(e)}", flush=True)
        return JSONResponse(status_code=500, content={'error': f'Failed to delete file: {str(e)}'})

@router.post('/delete')
def delete_prompt_file_noapi(name: str = Body(...)):
    return delete_prompt_file(name)

@router.post('/prompts/restore')
def restore_backup_file(request: dict = Body(...)):
    print(f"[restore_backup_file] received restore request: {request}", flush=True)
    
    # 从请求体中提取备份文件名和原文件名
    backup_name = request.get('backup_name')
    original_name = request.get('original_name')
    content = request.get('content')
    
    if not backup_name or not original_name or content is None:
        print(f"[restore_backup_file] missing required fields", flush=True)
        return JSONResponse(status_code=422, content={'error': 'Missing required fields: backup_name, original_name, content'})
    
    print(f"[restore_backup_file] backup: {backup_name}, original: {original_name}", flush=True)
    
    # 验证文件名
    import re
    if re.search(r'[<>:"/\\|?*]', original_name):
        print(f"[restore_backup_file] 原文件名包含非法字符: {original_name}", flush=True)
        return JSONResponse(status_code=422, content={'error': 'Original file name contains invalid characters'})
    
    try:
        # 检查备份文件是否存在
        backup_path = os.path.join(PROMPT_DIR, backup_name)
        if not os.path.isfile(backup_path):
            print(f"[restore_backup_file] backup not found: {backup_path}", flush=True)
            return JSONResponse(status_code=404, content={'error': 'Backup file not found'})
        
        # 检查原文件是否存在，如果存在则先备份
        original_path = os.path.join(PROMPT_DIR, original_name)
        if os.path.isfile(original_path):
            print(f"[restore_backup_file] original exists, creating pre-restore backup", flush=True)
            # Use simplified english suffix
            pre_restore_backup_name = f"{original_name}_pre_restore_backup"
            pre_restore_backup_path = os.path.join(PROMPT_DIR, pre_restore_backup_name)
            
            # 如果恢复前备份已存在，先删除
            if os.path.exists(pre_restore_backup_path):
                os.remove(pre_restore_backup_path)
                print(f"[restore_backup_file] remove old pre-restore backup: {pre_restore_backup_name}", flush=True)
            
            # 读取原文件内容并创建备份
            with open(original_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(pre_restore_backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            print(f"[restore_backup_file] created pre-restore backup: {pre_restore_backup_name}", flush=True)
        
        # Restore file
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[restore_backup_file] restored: {original_name}", flush=True)
        
        # Remove backup file
        os.remove(backup_path)
        print(f"[restore_backup_file] removed backup: {backup_name}", flush=True)
        
        return {'status': 'restored', 'original_name': original_name, 'backup_name': backup_name}
        
    except Exception as e:
        print(f"[restore_backup_file] restore failed: {str(e)}", flush=True)
        return JSONResponse(status_code=500, content={'error': f'Failed to restore file: {str(e)}'})

@router.get('/test')
def test_route():
    print("[test_route] 测试路由被调用", flush=True)
    return {"message": "test route works"} 