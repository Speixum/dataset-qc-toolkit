-- 数据集质检常用查询（SQLite 语法，其他数据库基本可直接用）
-- 表结构由 sql/demo.py 内置生成，字段如下：
--   images(image_id, name, split, width, height)
--   shapes(shape_id, image_id, label)
-- 运行：python sql/demo.py

-- 1. 每个类别的多边形数量，多的在前
SELECT label, COUNT(*) AS n
FROM shapes
GROUP BY label
ORDER BY n DESC;

-- 2. 每个类别覆盖了多少张图（同一张图同类多次出现只算一次）
SELECT label, COUNT(DISTINCT image_id) AS imgs
FROM shapes
GROUP BY label
ORDER BY imgs DESC;

-- 3. 只留下多边形数 >= 2 的类别（HAVING 筛的是分组后的结果）
SELECT label, COUNT(*) AS n
FROM shapes
GROUP BY label
HAVING COUNT(*) >= 2
ORDER BY n DESC;

-- 4. 训练 / 测试各有多少张图（检查划分比例）
SELECT split, COUNT(*) AS imgs
FROM images
GROUP BY split;

-- 5. 单图缺陷最多的前 3 张（找标注特别密的样本）
SELECT i.name, COUNT(*) AS shapes
FROM shapes s
JOIN images i ON i.image_id = s.image_id
GROUP BY i.name
ORDER BY shapes DESC
LIMIT 3;

-- 6. 每张图的第一个多边形（窗口函数取组内第一条）
SELECT name, label, rn
FROM (
  SELECT i.name,
         s.label,
         ROW_NUMBER() OVER (PARTITION BY s.image_id ORDER BY s.shape_id) AS rn
  FROM shapes s
  JOIN images i ON i.image_id = s.image_id
)
WHERE rn = 1
ORDER BY name;
