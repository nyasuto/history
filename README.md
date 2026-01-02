# hist - Safari履歴分析ツール 仕様書

## 1. 製品概要

macOSのSafariブラウザの履歴データベースを読み取り、分析・可視化するツール。
CLI、TUI（インタラクティブモード）、Webダッシュボードの3つのインターフェースを提供する。

### 対象プラットフォーム
- macOS（Safariの履歴DBにアクセスするため）

### 主要ユースケース
- 自分のブラウジング履歴を振り返る
- ドメイン別・時間帯別・日別の統計を確認
- 特定キーワードでの履歴検索
- 特定ドメインを除外した統計表示（イグノアリスト機能）

---

## 2. 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Go 1.25+ |
| データベース | SQLite3（読み取り専用） |
| SQLiteドライバ | `github.com/mattn/go-sqlite3` |
| TUIフレームワーク | `github.com/charmbracelet/bubbletea` + `lipgloss` |
| Webテンプレート | Go標準 `html/template` + `embed` |
| CSSフレームワーク | Tailwind CSS（CDN経由） |

---

## 3. Safari履歴データベース

### ファイルパス
```
~/Library/Safari/History.db
```

### 使用テーブル

#### `history_items`
履歴アイテム（URL単位）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | 主キー |
| url | TEXT | URL |
| domain_expansion | TEXT | ドメイン（NULLの場合あり） |
| visit_count | INTEGER | 累計訪問回数 |

#### `history_visits`
個別の訪問記録

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | 主キー |
| history_item | INTEGER | history_items.idへのFK |
| visit_time | REAL | Core Dataタイムスタンプ |
| title | TEXT | ページタイトル |

### Core Dataタイムスタンプ
Safariは**2001年1月1日 00:00:00 UTC**を基準とした秒数で時刻を保存している。

```go
var coreDataEpoch = time.Date(2001, 1, 1, 0, 0, 0, 0, time.UTC)

func convertCoreDataTimestamp(timestamp float64) time.Time {
    return coreDataEpoch.Add(time.Duration(timestamp * float64(time.Second)))
}
```

### 重要な注意点
- **読み取り専用**でオープンすること（`?mode=ro`）
- `domain_expansion`がNULLの場合はURLからドメインを抽出する必要がある
- macOSのフルディスクアクセス権限が必要

---

## 4. データ構造

### HistoryVisit（訪問記録）
```go
type HistoryVisit struct {
    URL       string    `json:"url"`
    Title     string    `json:"title"`
    Domain    string    `json:"domain"`
    VisitTime time.Time `json:"visit_time"`
}
```

### DomainStats（ドメイン統計）
```go
type DomainStats struct {
    Domain     string `json:"domain"`
    VisitCount int    `json:"visit_count"`
}
```

### PathStats（パス別統計）
```go
type PathStats struct {
    Path       string `json:"path"`
    Title      string `json:"title"`
    VisitCount int    `json:"visit_count"`
}
```

### DomainPathStats（ドメイン・パス階層統計）
```go
type DomainPathStats struct {
    Domain     string      `json:"domain"`
    TotalCount int         `json:"total_count"`
    Paths      []PathStats `json:"paths,omitempty"`
    HasPaths   bool        `json:"has_paths"`
    OtherCount int         `json:"other_count,omitempty"`  // 上位N件以外の合計
}
```

### ContentStats（コンテンツ統計 - ドメイン詳細ページ用）
```go
type ContentStats struct {
    URL        string `json:"url"`
    Title      string `json:"title"`
    Path       string `json:"path"`
    VisitCount int    `json:"visit_count"`
}
```

### HourlyStats（時間帯統計）
```go
type HourlyStats struct {
    Hour       int `json:"hour"`  // 0-23
    VisitCount int `json:"visit_count"`
}
```

### DailyStats（日別統計）
```go
type DailyStats struct {
    Date       string `json:"date"`  // YYYY-MM-DD
    VisitCount int    `json:"visit_count"`
}
```

### SearchFilter（検索・フィルタ条件）
```go
type SearchFilter struct {
    Keyword       string     // URL・タイトルの部分一致
    Domain        string     // ドメインフィルタ
    From          time.Time  // 開始日
    To            time.Time  // 終了日
    IgnoreDomains []string   // 除外ドメインリスト
}
```

---

## 5. 機能一覧

### 5.1 履歴取得
- 最近の訪問履歴をN件取得
- キーワード検索（URL・タイトル部分一致）
- ドメインフィルタ
- 日付範囲フィルタ
- ページネーション対応

### 5.2 統計機能
- **ドメイン別統計**: 訪問回数でランキング
- **ドメイン・パス階層統計**: ドメイン内のパス別訪問数（折りたたみUI）
- **時間帯別統計**: 0時〜23時の訪問分布
- **日別統計**: 過去N日間の訪問推移
- **コンテンツ統計**: 特定ドメイン内のURL別詳細

### 5.3 イグノアリスト
特定ドメインを統計から除外する機能。

**保存場所**: `~/.config/hist/ignore.txt`

**フォーマット**:
```
# コメント行
google.com
youtube.com
```

**マッチングロジック**:
- 完全一致: `google.com` → `google.com`
- サブドメイン: `google.com` → `mail.google.com`, `docs.google.com`

**CLIコマンド**:
```bash
hist --ignore-add google.com    # 追加
hist --ignore-remove google.com # 削除
hist --ignore-list              # 一覧表示
hist --no-ignore                # イグノア無効で実行
```

### 5.4 ベースドメイン抽出
サブドメインを統合してベースドメインで集計する。

**例**:
- `mail.google.com` → `google.com`
- `docs.google.com` → `google.com`
- `www.example.co.jp` → `example.co.jp`

**特殊TLDサポート**:
```go
var specialTLDs = []string{
    "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp", "gr.jp", "ed.jp",
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "com.au", "net.au", "org.au", "gov.au",
    "com.br", "org.br", "gov.br", "net.br",
}
```

---

## 6. CLIインターフェース

### 基本コマンド
```bash
# 履歴表示（デフォルト20件）
hist

# 全統計表示
hist --all

# 各種統計
hist --history        # 履歴一覧
hist --domain-stats   # ドメイン統計
hist --hourly         # 時間帯統計
hist --daily          # 日別統計
```

### フィルタオプション
```bash
hist --search "キーワード"       # キーワード検索
hist --domain example.com       # ドメインフィルタ
hist --from 2025-01-01          # 開始日
hist --to 2025-01-31            # 終了日
```

### 表示オプション
```bash
hist --limit 50         # 履歴表示件数
hist --domains 20       # ドメイン統計件数
hist --days 30          # 日別統計対象日数
```

### 出力形式
```bash
hist --json                    # JSON出力
hist --csv                     # CSV出力
hist --tsv                     # TSV出力
hist --output result.json      # ファイル出力
```

### モード切替
```bash
hist -i                 # インタラクティブモード
hist --interactive      # 同上
hist --serve            # Webサーバーモード
hist --serve --port 3000 # ポート指定
```

---

## 7. Webインターフェース

### ページ構成

| パス | ページ | 説明 |
|------|--------|------|
| `/` | ダッシュボード | 総訪問数、ドメイン別統計（階層表示）、最近の訪問 |
| `/domain?d=xxx` | ドメイン詳細 | 指定ドメインのコンテンツ一覧 |
| `/history` | 履歴一覧 | 全履歴（ページネーション、検索、フィルタ対応） |
| `/stats` | 統計ページ | 時間帯別・日別統計グラフ |

### API エンドポイント

| パス | メソッド | 説明 |
|------|----------|------|
| `/api/stats` | GET | 統計サマリ（総訪問数、ドメイン統計、時間帯統計） |
| `/api/stats/hourly` | GET | 時間帯別統計（?domain=xxx でフィルタ可） |
| `/api/stats/daily` | GET | 日別統計（?days=N, ?domain=xxx） |
| `/api/history` | GET | 履歴一覧（?limit=N） |
| `/api/domains` | GET | 全ドメイン一覧 |

### テンプレート構成
```
web/templates/
├── layout.html      # nav, footer の共通パーツ
├── dashboard.html   # ダッシュボード
├── domain.html      # ドメイン詳細
├── history.html     # 履歴一覧
└── stats.html       # 統計ページ
```

### テンプレート関数
```go
var templateFuncs = template.FuncMap{
    "formatTime": func(t time.Time) string { ... },  // "2006-01-02 15:04:05"
    "formatDate": func(t time.Time) string { ... },  // "2006-01-02"
    "truncate":   func(s string, length int) string { ... },
    "percentage": func(count, max int) float64 { ... },
    "add":        func(a, b int) int { return a + b },
    "sub":        func(a, b int) int { return a - b },
    "seq":        func(start, end int) []int { ... },  // ページネーション用
}
```

---

## 8. TUI（インタラクティブモード）

Bubbletea + Lipglossベースの端末UI。

### 操作方法
| キー | アクション |
|------|-----------|
| ↑/k | 上に移動 |
| ↓/j | 下に移動 |
| Enter | 詳細表示 |
| / | 検索モード |
| Esc | 検索クリア / 詳細閉じる |
| r | リロード |
| q | 終了 |

### 表示内容
- 履歴一覧（タイトル、訪問日時、ドメイン）
- 検索フィルタ
- 詳細ビュー（URL、タイトル、ドメイン、訪問日時）

---

## 9. ファイル構成

```
hist/
├── main.go              # エントリポイント、CLIパース、データ取得関数
├── server.go            # Webサーバー、ハンドラー
├── interactive.go       # TUIモード
├── config.go            # イグノアリスト管理
├── constants.go         # 定数定義
├── query_builder.go     # SQLクエリビルダー
├── main_test.go         # テスト
├── query_builder_test.go
├── interactive_test.go
├── go.mod
├── go.sum
├── Makefile            # make quality など
└── web/
    ├── templates/       # HTMLテンプレート
    │   ├── layout.html
    │   ├── dashboard.html
    │   ├── domain.html
    │   ├── history.html
    │   └── stats.html
    └── static/          # 静的ファイル（現在未使用）
```

---

## 10. 定数・デフォルト値

```go
// データベース
SafariHistoryPath = "Library/Safari/History.db"
SQLiteReadOnlyMode = "?mode=ro"

// CLI デフォルト
DefaultHistoryLimit = 20      // 履歴表示件数
DefaultDomainLimit = 10       // ドメイン統計件数
DefaultPathLimit = 5          // パス階層表示件数
DefaultDailyDays = 7          // 日別統計日数
DefaultWebPort = 8080         // Webサーバーポート

// Web UI
WebPageSize = 50              // 1ページあたり表示件数
WebDashboardRecentVisits = 5  // ダッシュボード最近の訪問
WebDefaultDays = 30           // 統計ページデフォルト日数

// TUI
DefaultPageSize = 15          // TUIページサイズ
MaxTitleLength = 60           // タイトル最大長
```

---

## 11. 開発上の注意点

### 11.1 権限
- macOSでSafari履歴DBにアクセスするには**フルディスクアクセス**権限が必要
- ターミナルアプリに対して権限を付与する

### 11.2 データベースアクセス
- 必ず**読み取り専用**モードで開く
- Safariが起動中でもロック競合を避けられる

### 11.3 domain_expansionのNULL対応
`history_items.domain_expansion`がNULLの場合がある。その場合はURLからドメインを抽出する。

```go
if v.Domain == "" {
    v.Domain = extractDomain(v.URL)
}
```

### 11.4 テスト
インメモリSQLiteでテスト用DBを作成してテストする。

```go
db, _ := sql.Open("sqlite3", ":memory:")
// テーブル作成・データ投入
```

### 11.5 品質チェック
```bash
make quality  # go test + go fmt + golangci-lint
```

---

## 12. 今後の拡張可能性

実装済みの機能に加え、以下の拡張が考えられる：

1. **エクスポート機能強化**: PDFレポート、グラフ画像
2. **統計の可視化**: Chart.jsなどを使ったグラフ表示
3. **リアルタイム更新**: WebSocketによる自動更新
4. **複数ブラウザ対応**: Chrome、Firefox履歴の読み取り
5. **タグ・カテゴリ機能**: 履歴の手動分類

---

## 13. ビルド・実行

```bash
# ビルド
go build -o hist .

# 実行
./hist                    # CLI
./hist -i                 # TUI
./hist --serve            # Webサーバー

# テスト
make quality
```

---

## 14. 参考：主要関数一覧

| 関数 | 説明 |
|------|------|
| `getRecentVisits(db, limit, filter)` | 履歴取得 |
| `getDomainStats(db, limit, filter)` | ドメイン統計取得 |
| `getDomainPathStats(db, limit, pathLimit, filter)` | ドメイン・パス階層統計 |
| `getContentStatsByDomain(db, domain, limit)` | 特定ドメインのコンテンツ統計 |
| `getHourlyStats(db, filter)` | 時間帯統計 |
| `getDailyStats(db, days, filter)` | 日別統計 |
| `getTotalVisits(db)` | 総訪問数 |
| `extractDomain(url)` | URLからドメイン抽出 |
| `extractBaseDomain(domain)` | ベースドメイン抽出 |
| `extractPath(url)` | URLからパス抽出 |
| `shouldIgnoreDomain(domain, ignoreDomains)` | イグノアチェック |
| `LoadIgnoreList()` | イグノアリスト読み込み |
