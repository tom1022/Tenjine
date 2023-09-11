
# このリポジトリについて

このプログラム群は一部の高等学校における研究活動の成果物をまとめる機関リポジトリのようなものです。高等学校において、過去の研究成果は通常、共有ファイルサーバに保存されていますが、これらの成果物があまり参照されていないという課題があります。そのため、高等学校に適した形で学術機関リポジトリを導入し、先行研究をより効果的に活用し、その価値を高めることを目的としています。

## 導入方法(開発環境向け)

### 最低限の導入

```shellscript
sudo apt install python3 python3-pip redis ffmpeg

git clone https://github.com/tom1022/hs-repository.git

cd hs-repository

pip install -r requirements.txt
```

### 設定方法

ディレクトリ直下にある`config.default.yml`を参考に`config.yml`としてコピーし設定例を参考に設定してください

### 実行方法

```shellscript
cd /path/to/hs-repository
flask run
```

## 注意事項

このリポジトリはアマチュアによって作成されたので美しく効率的なコードとは程遠いです

現在は開発中のため推奨はしませんが`configs/`にApacheやuwsgiの設定用ファイルが有るため一応運用はできます