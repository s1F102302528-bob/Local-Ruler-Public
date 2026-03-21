/* ========================================================================
   1. DOMContentLoaded イベントリスナー（ページの読み込み完了時に実行）
   ------------------------------------------------------------------------
   - 共通処理（プロジェクト名の取得）
   - 各ページの初期化処理（ページ判定と、対応する関数の呼び出し）
======================================================================== */
document.addEventListener('DOMContentLoaded', () => {

    // --- 共通機能：URLからプロジェクト名を取得し、ローカルストレージに保存 ---
    const urlParams = new URLSearchParams(window.location.search);
    const projectNameFromUrl = urlParams.get('projectName');
    if (projectNameFromUrl) {
        localStorage.setItem('currentProjectName', projectNameFromUrl);
    }
    const currentProjectName = localStorage.getItem('currentProjectName');

    // --- ページごとの処理（ルーター） ---

    // [ダッシュボードページ] の場合
    if (document.getElementById('project-plan-container')) {
        const dashboardTitle = document.getElementById('dashboard-title');
        if (dashboardTitle && currentProjectName) {
            dashboardTitle.textContent = `ダッシュボード: ${currentProjectName}`;
            document.title = `ダッシュボード | ${currentProjectName} | Chiiki-Navi`;
        }
        // プロジェクト計画機能の初期化
        initializeProjectPlan(currentProjectName);
    }
    
    // [ITスキル学習ページ] の場合
    const skillSearchBtn = document.getElementById('skill-search-btn');
    const skillSearchInput = document.getElementById('skill-search-input');
    if (skillSearchBtn) {
        skillSearchBtn.addEventListener('click', () => {
            const query = skillSearchInput.value;
            if (query) {
                // サイト検索リンクを生成する関数を呼び出す
                generateSiteSearchLinks(query);
            }
        });
    }

    // [設定ページ] の場合
    const projectNameInput = document.getElementById('projectName');
    if (projectNameInput && currentProjectName) {
        projectNameInput.value = currentProjectName;
    }

    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const mainNav = document.querySelector('.main-nav');

    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            // メニューの表示/非表示を切り替え
            mainNav.classList.toggle('active');

            // アイコンの切り替え（三本線 ⇔ バツ印）
            const icon = menuToggle.querySelector('i');
            if (mainNav.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }

});

/* ========================================================================
   2. メイン機能の関数
   ------------------------------------------------------------------------
   - 各ページから呼び出される主要な関数を定義
======================================================================== */

/**
 * [ダッシュボード] プロジェクト計画機能の初期化とイベントリスナーの設定
 * @param {string} projectName - 現在のプロジェクト名
 */
function initializeProjectPlan(projectName) {
    if (!projectName) return;

    // --- 必要なDOM要素を取得 ---
    const planContainer = document.getElementById('project-plan-container');
    const cardActions = document.querySelector('.card-actions');
    const storageKey = `project_plan_${projectName}`;

    // --- 内部ヘルパー関数：データ処理 ---
    const getPlanData = () => JSON.parse(localStorage.getItem(storageKey)) || null;
    const savePlanData = (data) => localStorage.setItem(storageKey, JSON.stringify(data));

    // --- 内部ヘルパー関数：UI描画 ---
    
    // 表示モードのUIを生成
    const renderViewMode = (data) => {
        planContainer.innerHTML = `
            <div class="plan-view">
                <h4>最終目標</h4>
                <p>${data.finalGoal || '未設定'}</p>
                <hr>
                <div id="phases-view-container">
                    ${data.phases.map((phase, pIndex) => `
                        <div class="phase-view">
                            <h5>フェーズ ${pIndex + 1}: ${phase.name}</h5>
                            <ul>
                                ${phase.milestones.map(ms => `<li>${ms}</li>`).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        cardActions.innerHTML = `<button class="btn btn-secondary" id="edit-plan-btn"><i class="fas fa-pencil-alt"></i> 編集</button>`;
        // 表示モードのボタンにイベントリスナーを設定
        document.getElementById('edit-plan-btn').addEventListener('click', () => renderEditMode(data));
    };
    
    // 編集モードのUIを生成
    const renderEditMode = (data = { finalGoal: '', phases: [] }) => {
        planContainer.innerHTML = `
            <div class="form-group">
                <label>最終目標:</label>
                <input type="text" id="final-goal-input" class="form-control" value="${data.finalGoal}">
            </div>
            <hr>
            <div id="phases-edit-container">
                ${data.phases.map((phase, pIndex) => createPhaseEditHTML(phase, pIndex)).join('')}
            </div>
            <button class="btn btn-secondary" id="add-phase-btn"><i class="fas fa-plus"></i> フェーズを追加</button>
        `;
        cardActions.innerHTML = `<button class="btn" id="save-plan-btn"><i class="fas fa-save"></i> 保存</button>`;

        // 編集モードのボタンにイベントリスナーを再設定
        document.getElementById('save-plan-btn').addEventListener('click', handleSave);
        document.getElementById('add-phase-btn').addEventListener('click', handleAddPhase);
        planContainer.addEventListener('click', handleDynamicClicks);
    };

    // 編集モードの「フェーズ」部分のHTMLを生成
    const createPhaseEditHTML = (phase, pIndex) => `
        <div class="phase-edit-group" data-phase-index="${pIndex}">
            <div class="form-group">
                <label>フェーズ ${pIndex + 1} の名前:</label>
                <div class="input-with-button">
                    <input type="text" class="form-control phase-name-input" value="${phase.name}">
                    <button class="btn-icon remove-phase-btn" title="フェーズを削除"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
            <div class="milestones-container">
                ${phase.milestones.map((ms, mIndex) => `
                    <div class="input-with-button">
                        <input type="text" class="form-control milestone-input" value="${ms}" placeholder="マイルストーンを入力">
                        <button class="btn-icon remove-milestone-btn" title="マイルストーンを削除"><i class="fas fa-times"></i></button>
                    </div>
                `).join('')}
            </div>
            <button class="btn-link add-milestone-btn">＋ マイルストーンを追加</button>
        </div>
    `;

    // --- 内部ヘルパー関数：イベントハンドラ ---

    // 保存ボタンの処理
    const handleSave = () => {
        const finalGoal = document.getElementById('final-goal-input').value;
        const phases = [];
        document.querySelectorAll('.phase-edit-group').forEach(phaseEl => {
            const phaseName = phaseEl.querySelector('.phase-name-input').value;
            const milestones = [];
            phaseEl.querySelectorAll('.milestone-input').forEach(msInput => {
                if(msInput.value) milestones.push(msInput.value);
            });
            if (phaseName) {
                phases.push({ name: phaseName, milestones });
            }
        });
        const newData = { finalGoal, phases };
        savePlanData(newData);
        renderViewMode(newData); // 保存後に表示モードに切り替え
    };

    // 「フェーズを追加」ボタンの処理
    const handleAddPhase = () => {
        const container = document.getElementById('phases-edit-container');
        const newIndex = container.children.length;
        const newPhaseHTML = createPhaseEditHTML({ name: '', milestones: [''] }, newIndex);
        container.insertAdjacentHTML('beforeend', newPhaseHTML);
    };
    
    // 動的に追加された要素（削除ボタンなど）のクリック処理（イベント委任）
    const handleDynamicClicks = (e) => {
        // 「マイルストーンを追加」
        if (e.target.closest('.add-milestone-btn')) {
            e.preventDefault();
            const container = e.target.closest('.phase-edit-group').querySelector('.milestones-container');
            container.insertAdjacentHTML('beforeend', `
                <div class="input-with-button">
                    <input type="text" class="form-control milestone-input" placeholder="マイルストーンを入力">
                    <button class="btn-icon remove-milestone-btn" title="マイルストーンを削除"><i class="fas fa-times"></i></button>
                </div>
            `);
        }
        // 「フェーズを削除」
        if (e.target.closest('.remove-phase-btn')) {
            e.target.closest('.phase-edit-group').remove();
        }
        // 「マイルストーンを削除」
        if (e.target.closest('.remove-milestone-btn')) {
            e.target.closest('.input-with-button').remove();
        }
    };
    
    // --- 初期表示処理 ---
    const initialData = getPlanData();
    if (initialData) {
        renderViewMode(initialData); // データがあれば表示モード
    } else {
        renderEditMode(); // データがなければ編集モード
    }
}

/**
 * [ITスキル学習] 信頼できるIT学習サイトの検索リンクを生成して表示する
 * @param {string} query - ユーザーが入力した検索キーワード
 */
function generateSiteSearchLinks(query) {
    const container = document.getElementById('learning-results-container');
    if (!container) return;

    // 検索対象とする信頼できるサイトのリスト
    const reliableSites = [
        {
            name: 'MDN Web Docs (Web技術の辞書)',
            searchUrl: `https://developer.mozilla.org/ja/search?q=${encodeURIComponent(query)}`
        },
        {
            name: 'ドットインストール (動画学習)',
            searchUrl: `https://dotinstall.com/search?q=${encodeURIComponent(query)}`
        },
        {
            name: 'YouTube',
            searchUrl: `https://youtube.com/search?q=${encodeURIComponent(query)}`
        }
    ];

    // コンテナをクリア
    container.innerHTML = ''; 

    // 各サイトへの検索リンクをHTMLとして生成
    reliableSites.forEach(site => {
        const linkElement = document.createElement('a');
        linkElement.href = site.searchUrl;
        linkElement.target = '_blank'; // 新しいタブで開く
        linkElement.textContent = `「${query}」を ${site.name} で検索する`;
        linkElement.className = 'search-result-link'; // スタイルはCSS側で定義
        container.appendChild(linkElement);
    });

    if (reliableSites.length === 0) {
        container.innerHTML = '<p>検索対象サイトが設定されていません。</p>';
    }
}