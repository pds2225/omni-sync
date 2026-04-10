"""
agents/asset_agent.py
----------------------
이미지 경로·제목 정리 에이전트

담당 영역:
  - content["assets"] 목록 검증 및 정리
  - 이미지 최대 1장 제한 (데이터바우처 규정)
  - 이미지 파일 존재 여부 확인
  - 제목 미입력 시 기본값 부여
  - RenderAgent가 inject_image()를 호출할 수 있도록 content["images"] 포맷으로 변환

주의:
  이 에이전트는 이미지를 생성하거나 AI로 만들지 않습니다.
  파일이 없으면 오류로 처리하고 렌더링 단계에서 건너뜁니다.
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

        # ── 최대 1장 제한 검사 ──────────────────────────────────
        if len(assets) > 1:
            self._warnings.append(
                f"이미지가 {len(assets)}장 입력되었습니다. "
                "데이터바우처 규정상 1장만 삽입되며 나머지는 무시됩니다."
            )
            assets = assets[:1]  # 첫 번째만 사용

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
