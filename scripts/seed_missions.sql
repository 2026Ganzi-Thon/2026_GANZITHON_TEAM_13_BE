-- 쉼포: 확정된 기본 미션 18개
-- 실행 전 현재 접속한 DB가 로컬 개발용 mission DB인지 확인하세요.
-- 기존 동일 ID를 가진 미션은 아래 확정 목록으로 갱신됩니다.
-- 기존 미션 수행 기록이 있다면 해당 ID의 의미가 바뀌지 않는지 먼저 확인하세요.
-- description은 팀에서 확정하지 않아 임시 문구를 사용합니다.
USE mission;

START TRANSACTION;

INSERT INTO missions_mission
    (id, title, description, category, duration_seconds, image_url, is_active)
VALUES
    (1, '쓰레기 치우기', '쓰레기 치우기 미션', 'INDOOR', 60, NULL, TRUE),
    (2, '물 한 잔 마시기', '물 한 잔 마시기 미션', 'INDOOR', 60, NULL, TRUE),
    (3, '분리 수거 하기', '분리 수거 하기 미션', 'INDOOR', 300, NULL, TRUE),
    (4, '집 안 환기하기', '집 안 환기하기 미션', 'INDOOR', 60, NULL, TRUE),
    (5, '옷 개기', '옷 개기 미션', 'INDOOR', 300, NULL, TRUE),
    (6, '웹툰 한 편 보기', '웹툰 한 편 보기 미션', 'INDOOR', 60, NULL, TRUE),
    (7, '좋아하는 음악 듣기', '좋아하는 음악 듣기 미션', 'INDOOR', 180, NULL, TRUE),
    (8, '책상 정리하기', '책상 정리하기 미션', 'INDOOR', 60, NULL, TRUE),
    (9, '스트레칭 하기', '스트레칭 하기 미션', 'INDOOR', 60, NULL, TRUE),
    (10, '스쿼트 5개 하기', '스쿼트 5개 하기 미션', 'INDOOR', 60, NULL, TRUE),
    (11, '주변 산책하기', '주변 산책하기 미션', 'OUTDOOR', 600, NULL, TRUE),
    (12, '근처 편의점에서 신상 제품 하나 사기', '편의점 방문 미션', 'OUTDOOR', 600, NULL, TRUE),
    (13, '도서관에서 책 빌리기', '도서관 방문 미션', 'OUTDOOR', 900, NULL, TRUE),
    (14, '동물 사진찍기', '동물 사진찍기 미션', 'OUTDOOR', 600, NULL, TRUE),
    (15, '하늘 사진 찍기', '하늘 사진 찍기 미션', 'OUTDOOR', 600, NULL, TRUE),
    (16, '길거리 쓰레기 줍기', '길거리 쓰레기 줍기 미션', 'OUTDOOR', 600, NULL, TRUE),
    (17, '들 꽃 사진 찍기', '들 꽃 사진 찍기 미션', 'OUTDOOR', 600, NULL, TRUE),
    (18, '근처 공원 한 바퀴 돌기', '공원 산책 미션', 'OUTDOOR', 900, NULL, TRUE)
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    description = VALUES(description),
    category = VALUES(category),
    duration_seconds = VALUES(duration_seconds),
    image_url = VALUES(image_url),
    is_active = VALUES(is_active);

COMMIT;

SELECT category, COUNT(*) AS mission_count
FROM missions_mission
WHERE id BETWEEN 1 AND 18
GROUP BY category;

SELECT id, title, category, duration_seconds
FROM missions_mission
WHERE id BETWEEN 1 AND 18
ORDER BY id;
