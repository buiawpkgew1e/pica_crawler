# -*- coding: utf-8 -*-

list2 = [
    "すらいむのかんむり (かんむり)", "ツリサス", "ヤバ谷らんど (ほみなみあ)", "即オチ少女 (鏡乃もちこ)", "ねことうふ", "共謀猫 (春ヲ、 不二岳、 8205)", "もけぷーず",
    "原作：富士防人  作画：外冈马骨", "CHARAN PORAN (猫乃またたび)", "Tera Stellar (小山内にい)", "伊藤屋", "おひつじ", "おひつじ", "愛兒(HENJIN69)", "アラタ", "クリスタルな洋介",
    "SeaFox (霧咲白狐)", "すえみつぢっか", "シザリオン (しーざー)", "憑依k", "DA HOOTCH (新堂エル)", "ColdBloodedTwilight", "DA HOOTCH (新堂エル)", "ciaociao (あらきかなお)",
    "柊ぽぷら", "醉卧星河", "絵を描くマン (Eman)", "性轉換", "Okayushop (Okayu)", "おひつじ", "自宅 (へも)", "なかよし産婦人科 (まてつ)", "KH. (有紀)", "中川優", "かるま龍狼",
    "桃河馬", "ろくでなしの詩(俊)", "神谷ズズ", "浅野屋 (キッツ)", "UTEN+ (雨天あめか)", "L.P.E.G. (まる寝子)", "恥辱庵", "炭酸プロテイン柏木", "眼ん月堂 (至室)", "银发贫乳控",
    "矢吹健太朗", "海鮮堂(マクジラ)", "柊ぽぷら", "史鬼匠人", "DAGASI", "Siesta (九廊)", "つゆだくシュガー (すずしも)", "モモモーモー伯爵", "Imitation Moon (成海優)", "條仔、あるべんと",
    "すえみつぢっか", "おたまジャグジー (たまの父)", "みこやん", "夢先案内回覧版 (ひろひろき)", "ノボッチ製作所 (南雲龍一)", "くまQM", "あむぁいおかし製作所 (かいわれ大根、あほげきのこ)",
    "Duckgu", "山本同人", "pulltop", "いづみ(CHIPS)", "わろみん家 (わろみん)", "カネコナオヤ", "聖華快楽書店 (エルトリア、夜空さくら、nikujaga)", "タカスギコウ", "憑依の刻",
    "ジンギスカンの玉葱は俺の嫁 (谷口さん)", "あむぁいおかし製作所 (ゆーきぃ)", "Arisane (Arisa Yoshi)", "小飛鼠", "影魔尤影", "マメック星", "拍手喝罪（我宮てれさ）", "jm600r",
    "あむぁいおかし製作所 (つく丸、なまむぎ)", "ZPT (ポミヲ)", "あむぁいおかし製作所 (倉塚りこ)", "橘由宇", "若宮参太", "花巻かえる", "不明", "アンソロジー", "龍企画 (龍炎狼牙)",
    "竹とんぼ (菜葉)", "MAX&Cool", "くれじっと", "狐梅珈琲店 (鹽、彩月あたん)", "そらりれゆ", "奥森ボウイ", "永田まりあ", "RIX (マミヤ)", "うどんや (鬼月あるちゅ、ZAN)",
    "U.R.C(桃屋しょう貓)", "羽贺ソウケン 長尾件", "くろむら基人", "STUDIO&PIM-DOG", "ハシモトミツ", "THE猥談 (鬱ノ宮うかつ)", "しまなみ (あーきぺらご)", "ノードラッグハイテンション(水乃カルキ)",
    "ふずめ", "谷口さん", "桃純 (ももずみ純)", "ゆきしずく (ながねこ)", "うえにあるみかん", "きのこのみ (konomi)", "ciaociao (あらきかなお)", "Duokuma", "矢吹健太郎", "たまの父",
    "Asunaro Neat. (ろんな)", "Tempest (伊巻てん、温野りょく)", "BEHIND THE MASK (蜜子。)", "KABA", "Marialite (ゆーきぃ)", "吉田悟郎商會 (吉田悟郎)", "ウェルト",
    "もげたま (田中森よこた)", "千之 ナイフ(Senno Knife)(千之刃)", "高崎たけまる", "折川", "TSF no F (べってぃ)", "あむぁいおかし製作所 (かいわれ大根、つく丸)", "晴濑ひろき",
    "不二河聡", "伊佐美ノゾミ", "狼亮輔", "egoistic media(棗ふみこ)", "安治ぽん太郎", "アラタ", "エレクトさわる", "黑澤清崇", "牧野坂シンイチ", "Blue Crest (蒼野アキラ)"
]

# 使用set去除重复项
new_list = list(set(list2))
print(f"去重后列表长度为 {len(new_list)}")
print(f"去重后列表为 {new_list}")

output_file_path = 'new_list.txt'

try:
    with open(output_file_path, 'w', encoding='utf-8') as file:
        for item in new_list:
            file.write(f"{item}\n")
    print(f"结果已保存到 {output_file_path} 文件中。")
except Exception as e:
    print(f"保存文件时发生错误: {e}")
