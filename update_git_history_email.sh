#!/bin/sh

# 脚本功能：替换 Git 提交历史中的邮箱地址
# 作者: fxbin

# 要替换的旧邮箱
OLD_EMAIL="test@demo.com"
# 新的邮箱地址
NEW_EMAIL="newtest@demo.com"
# 要修改的提交者名称 (如果需要，否则保持不变)
CORRECT_NAME="test"
# 要修改的提交者邮箱
CORRECT_EMAIL="newtest@demo.com"

# 使用 filter-branch 命令修改提交历史
# --env-filter 选项允许我们修改环境变量，这些变量在重写提交时会被 Git 使用
git filter-branch --env-filter '
if [ "$GIT_COMMITTER_EMAIL" = "'$OLD_EMAIL'" ]
then
    export GIT_COMMITTER_NAME="'$CORRECT_NAME'"
    export GIT_COMMITTER_EMAIL="'$CORRECT_EMAIL'"
fi
if [ "$GIT_AUTHOR_EMAIL" = "'$OLD_EMAIL'" ]
then
    export GIT_AUTHOR_NAME="'$CORRECT_NAME'"
    export GIT_AUTHOR_EMAIL="'$CORRECT_EMAIL'"
fi
' --tag-name-filter cat -- --branches --tags

# 提示：
# 1. 在执行此脚本之前，请务必备份您的仓库！这是一个破坏性操作。
# 2. 执行完毕后，您需要强制推送到远程仓库以更新历史记录：
#    git push --force --tags origin 'refs/heads/*'
# 3. 如果您在 GitHub 上操作，并且仓库受保护分支的限制，您可能需要暂时取消保护才能强制推送。
# 4. 此操作会改变提交的 SHA-1 值，如果您与他人协作，请确保所有人都知晓此更改。

echo "Git 历史邮箱替换完成。"
echo "请检查提交历史，如果一切正常，请使用 'git push --force --tags origin \'refs/heads/*\' 命令强制推送到远程仓库。"
echo "重要提示：强制推送会覆盖远程历史，请谨慎操作，并确保已备份仓库。"