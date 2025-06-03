# script-toolbox
Script Toolbox

## 脚本工具箱

### Git 提交历史邮箱更新脚本 (update_git_history_email.sh)

这个脚本用于批量修改 Git 仓库中的提交历史中的邮箱地址。当您需要更新 Git 提交历史中的邮箱信息时，这个工具可以帮助您快速完成操作。

#### 使用方法

1. 编辑脚本中的以下变量：
   ```bash
   OLD_EMAIL="test@demo.com"      # 要替换的旧邮箱
   NEW_EMAIL="newtest@demo.com"   # 新的邮箱地址
   CORRECT_NAME="test"            # 要修改的提交者名称
   CORRECT_EMAIL="newtest@demo.com" # 要修改的提交者邮箱
   ```

2. 在 Git 仓库根目录下运行脚本：
   ```bash
   chmod +x update_git_history_email.sh
   ./update_git_history_email.sh
   ```

#### 注意事项

- **重要**：执行脚本前请务必备份您的仓库，因为这是一个不可逆的操作
- 脚本执行完成后，需要使用 `git push --force --tags origin 'refs/heads/*'` 强制推送到远程仓库
- 如果是 GitHub 保护分支，可能需要临时解除保护才能强制推送
- 此操作会改变所有提交的 SHA-1 值，如果是团队协作项目，请确保通知所有相关成员

#### 使用场景

- 更改错误的提交邮箱地址
- 统一团队成员的提交邮箱格式
- 更新个人或组织的邮箱信息
