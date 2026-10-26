# 繁中有聲書寫作 V2

Traditional Chinese audiobook writing skill for TTS-ready scripts. This skill does not generate audio.

## 用途

以繁體中文與台灣用語規劃有聲作品，支援新書寫作、紙本改編、Podbook、單人與雙人配音稿，以及聲音製作與校聽的文字規格。

## 使用方式

從 [SKILL.md](SKILL.md) 開始，依任務讀取 `references/` 中的寫作方法、題材模板與檢查規範。將完整目錄交給支援本類 Skill 的代理工具使用，保留參照檔案的相對路徑。

文字稿可用內附工具預檢：

```sh
python3 scripts/style_check.py path/to/manuscript.md --mode auto
python3 scripts/style_check.py path/to/manuscript.md --mode auto --format json
```

支援 `.txt`、`.md`、`.markdown` 與 `.docx`。規則檢查不取代事實查證、著作授權確認或人工校聽。

## 範圍

本專案只提供寫作方法、文字稿與製作規格；不執行 TTS、音訊生成、剪輯、混音或發布。音訊製作需另行選擇工具並取得授權。
