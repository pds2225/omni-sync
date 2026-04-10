"""
asset_agent.py — 이미지 자산 검증 에이전트
==========================================
역할: project_input.json의 assets 배열에서 파일 존재 여부를 확인.

처리:
    assets[].path 에 대해 os.path.exists() 확인
    존재하면 content["_assets"] 에 추가
    없으면 경고 발생 (QA warning)

현재 한계:
    이미지 해상도·비율 검증 미구현
    이미지 포맷 변환 미구현 (.jpg → .png 등)
"""
from __future__ import annotations
import os


# 데이터바우처 이미지 삽입 위치 키워드 (DOCX 내 헤딩 텍스트)
IMAGE_KEYWORD = "관련 이미지"

# 기본 이미지 크기 (cm)
DEFAULT_WIDTH_CM  = 14.0
DEFAULT_HEIGHT_CM = 9.0


class AssetAgent:
    """
    이미지 정리 에이전트.

    run(content) → content  (content["images"] 키 추가)
    """

    def __init__(self):
        self._warnings: list[str] = []
        self._errors:   list[str] = []
        self._images_ready: int = 0

    # ── 메인 실행 ──────────────────────────────────────────────
    def run(self, content: dict) -> dict:
        """
        content["assets"]를 검증하고, BizPlanInjector의 images 포맷으로 변환.

        추가되는 키:
          content["images"] : [{"keyword": str, "image_path": str,
                                "width_cm": float, "height_cm": float, "align": str}]
        """
        assets = content.get("assets", [])
        images = []

        for asset in assets:
            path  = asset.get("path", "").strip()
            title = asset.get("title", "").strip()

            # ── 경로 검증 ────────────────────────────────────────
            if not path:
                self._errors.append("이미지 경로가 비어 있습니다. 이미지 삽입을 건너뜁니다.")
                continue

            if not os.path.exists(path):
                self._warnings.append(
                    f"이미지 파일을 찾을 수 없습니다: {path}. 삽입이 건너뜁니다."
                )
                continue

            # ── 제목 보완 ────────────────────────────────────────
            if not title:
                fname = os.path.splitext(os.path.basename(path))[0]
                title = fname
                self._warnings.append(
                    f"이미지 제목 미입력. 파일명을 제목으로 사용합니다: '{title}'"
                )

            images.append({
                "keyword":    IMAGE_KEYWORD,
                "image_path": path,
                "width_cm":   asset.get("width_cm",  DEFAULT_WIDTH_CM),
                "height_cm":  asset.get("height_cm", DEFAULT_HEIGHT_CM),
                "align":      asset.get("align", "center"),
                "_title":     title,   # QA·로그용 (렌더링에 직접 사용 안 함)
            })
            self._images_ready += 1

        content["images"]          = images
        content["_asset_warnings"] = self._warnings
        content["_asset_errors"]   = self._errors
        return content

    # ── 상태 요약 ──────────────────────────────────────────────
    def summary(self) -> str:
        return (f"images_ready={self._images_ready}, "
                f"warnings={len(self._warnings)}, errors={len(self._errors)}")
