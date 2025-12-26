/**
 * Waiting Content for Blog Automation UI
 * 
 * Provides rotating messages, tips, and motivational quotes
 * to display during long-running processes.
 */

const waitingContent = {
    // 励まし・労いのメッセージ（メイン）
    cheerMessages: [
        "今日も一日お疲れ様です！",
        "あなたの技術で、きっと誰かが笑顔になります",
        "素敵なブログ記事になりそうですね！",
        "いつも丁寧な投稿ありがとうございます",
        "継続は力なり、ですね！",
        "ホットペッパービューティーの更新、素晴らしいです",
        "お客様に想いが届きますように",
        "AIと一緒に、魅力的な発信を続けましょう",
        "一休みして、コーヒーでもいかがですか？",
        "その調子です！応援しています"
    ],

    // システム稼働中の演出メッセージ（サブ）
    systemStatus: {
        preparing: [
            "画像を最適化しています...",
            "AIが構成を整理しています...",
            "サーバーの準備をしています..."
        ],
        auth: [
            "SALON BOARDへ安全に接続しています...",
            "認証情報を確認しています...",
            "セキュリティチェックを実行中..."
        ],
        posting: [
            "心を込めて記事を入力中...",
            "レイアウトを調整しています...",
            "画像をアップロードしています..."
        ],
        saving: [
            "投稿結果を確認しています...",
            "仕上げの処理を行っています...",
            "もうすぐ完了します！"
        ]
    },

    /**
     * Get a random cheer message
     * @returns {string} Random message
     */
    getRandomCheer() {
        const index = Math.floor(Math.random() * this.cheerMessages.length);
        return this.cheerMessages[index];
    },

    /**
     * Get system message based on step
     * @param {string} stepId - Current step ID
     * @returns {string} System message
     */
    getSystemMessage(stepId) {
        // Map step IDs to keys
        const map = {
            'STEP_PREPARING': 'preparing',
            'STEP_AUTH': 'auth',
            'STEP_POSTING': 'posting',
            'STEP_SAVING': 'saving'
        };
        
        const key = map[stepId] || 'preparing';
        const messages = this.systemStatus[key];
        const index = Math.floor(Math.random() * messages.length);
        return messages[index];
    }
};

// Export to window
window.waitingContent = waitingContent;
