"""ADB 截图与设备管理 API。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.wrappers.adb_wrapper import ADBWrapper
from app.security import get_current_user
from app.models.user import User

router = APIRouter()

# ── Pydantic Schemas ────────────────────────────────────────

class DeviceInfo(BaseModel):
    device_id: str
    state: str
    resolution: tuple[int, int]
    model: Optional[str] = None
    product: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    available: bool
    server_running: bool
    devices: list[DeviceInfo]
    default_device: Optional[DeviceInfo] = None


class ADBStatusResponse(BaseModel):
    adb_available: bool
    server_running: bool
    connected: bool
    device: Optional[DeviceInfo] = None
    message: str


class ScreenshotResponse(BaseModel):
    success: bool
    device_id: Optional[str] = None
    resolution: Optional[tuple[int, int]] = None
    message: str


class InferenceRequest(BaseModel):
    device_id: Optional[str] = None
    mode: str = "hybrid"  # "hybrid" | "template" | "yolo"
    yolo_conf: float = 0.25
    template_conf: float = 0.85


class DetectionItem(BaseModel):
    cls: str
    x: int
    y: int
    w: int
    h: int
    conf: float
    source: str


class InferenceResponse(BaseModel):
    success: bool
    device_id: Optional[str] = None
    resolution: Optional[tuple[int, int]] = None
    detections: list[DetectionItem]
    annotated_image_url: Optional[str] = None
    message: str


# ── 路由实现 ──────────────────────────────────────────────────

@router.get("/status", response_model=ADBStatusResponse)
async def get_adb_status(
    device_id: Optional[str] = Query(default=None, description="设备 ID"),
    current_user: User = Depends(get_current_user),
):
    """检测 ADB 连接状态。"""
    adb = ADBWrapper(device_id=device_id)

    available = adb.check_adb_available()
    if not available:
        return ADBStatusResponse(
            adb_available=False,
            server_running=False,
            connected=False,
            device=None,
            message="ADB 命令不可用，请确认 adb 已安装并加入 PATH",
        )

    server_running = adb.check_server_running()
    if not server_running:
        return ADBStatusResponse(
            adb_available=True,
            server_running=False,
            connected=False,
            device=None,
            message="ADB server 未运行",
        )

    devices = adb.list_devices()
    default_device = None
    for d in devices:
        if d.is_connected:
            if device_id is None or d.device_id == device_id:
                default_device = d
            if device_id and d.device_id == device_id:
                break

    if default_device is None:
        return ADBStatusResponse(
            adb_available=True,
            server_running=True,
            connected=False,
            device=None,
            message="未检测到已连接的 Android 设备，请确保设备已通过 USB 连接并启用 USB 调试",
        )

    return ADBStatusResponse(
        adb_available=True,
        server_running=True,
        connected=True,
        device=DeviceInfo(
            device_id=default_device.device_id,
            state=default_device.state,
            resolution=default_device.resolution,
            model=default_device.model,
            product=default_device.product,
        ),
        message="设备已连接",
    )


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    current_user: User = Depends(get_current_user),
):
    """列出所有已连接的 ADB 设备。"""
    adb = ADBWrapper()

    available = adb.check_adb_available()
    if not available:
        return DeviceListResponse(
            available=False,
            server_running=False,
            devices=[],
            default_device=None,
        )

    server_running = adb.check_server_running()

    try:
        devices = adb.list_devices()
    except RuntimeError:
        return DeviceListResponse(
            available=True,
            server_running=server_running,
            devices=[],
            default_device=None,
        )

    connected = [d for d in devices if d.is_connected]
    default = connected[0] if connected else None

    return DeviceListResponse(
        available=True,
        server_running=server_running,
        devices=[
            DeviceInfo(
                device_id=d.device_id,
                state=d.state,
                resolution=d.resolution,
                model=d.model,
                product=d.product,
            )
            for d in devices
        ],
        default_device=(
            DeviceInfo(
                device_id=default.device_id,
                state=default.state,
                resolution=default.resolution,
                model=default.model,
                product=default.product,
            )
            if default
            else None
        ),
    )


@router.get("/screenshot")
async def take_screenshot(
    device_id: Optional[str] = Query(default=None, description="设备 ID，为空则使用第一个已连接设备"),
    current_user: User = Depends(get_current_user),
):
    """截取设备屏幕并返回 PNG 图片流。"""
    adb = ADBWrapper(device_id=device_id)

    # Find device
    if device_id:
        devices = adb.list_devices()
        target = next((d for d in devices if d.device_id == device_id and d.is_connected), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"设备 {device_id} 未连接")
    else:
        target = adb.get_connected_device()
        if not target:
            raise HTTPException(
                status_code=503,
                detail="未检测到已连接的 Android 设备，请确保设备已启用 USB 调试",
            )

    try:
        png_bytes = adb.capture_to_bytes()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        iter([png_bytes]),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="screenshot_{device_id or "default"}.png"',
            "X-Device-ID": target.device_id,
            "X-Resolution": f"{target.resolution[0]}x{target.resolution[1]}",
        },
    )


@router.get("/inference", response_model=InferenceResponse)
async def run_inference(
    device_id: Optional[str] = Query(default=None, description="设备 ID"),
    mode: str = Query(default="hybrid", description="检测模式: hybrid/template/yolo"),
    yolo_conf: float = Query(default=0.25, ge=0.0, le=1.0, description="YOLO 置信度阈值"),
    template_conf: float = Query(default=0.85, ge=0.0, le=1.0, description="模板匹配置信度阈值"),
    current_user: User = Depends(get_current_user),
):
    """截取屏幕并运行推理检测，返回检测结果和标注图片。"""
    from app.wrappers import DetectorWrapper, TemplateWrapper
    import cv2
    import numpy as np

    adb = ADBWrapper(device_id=device_id)

    # Find device
    if device_id:
        devices = adb.list_devices()
        target = next((d for d in devices if d.device_id == device_id and d.is_connected), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"设备 {device_id} 未连接")
    else:
        target = adb.get_connected_device()
        if not target:
            raise HTTPException(status_code=503, detail="未检测到已连接的 Android 设备")

    # Capture screen
    try:
        frame = adb.capture_frame()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    detections = []
    annotated_bytes: Optional[bytes] = None

    try:
        if mode in ("hybrid", "template"):
            tw = TemplateWrapper(threshold=template_conf)
            if tw.is_ready:
                dets = tw.match_all(frame)
                detections.extend([d.to_dict() for d in dets])

        if mode in ("hybrid", "yolo"):
            dw = DetectorWrapper(yolo_conf=yolo_conf)
            if dw.is_ready:
                dets = dw.detect(frame)
                detections.extend([d.to_dict() for d in dets])
    except RuntimeError:
        pass  # Detector not ready — return raw screenshot

    # Generate annotated image if we have detections
    if detections:
        try:
            dw = DetectorWrapper(yolo_conf=yolo_conf)
            if dw.is_ready:
                raw = [
                    type("D", (), {**d, "source": d["source"]})()  # noqa
                    for d in detections
                ]
                annotated = dw.draw(frame, raw)
                _, buf = cv2.imencode(".png", annotated)
                annotated_bytes = buf.tobytes()
        except Exception:
            pass

    return InferenceResponse(
        success=True,
        device_id=target.device_id,
        resolution=target.resolution,
        detections=[DetectionItem(**d) for d in detections],
        message=f"检测完成，发现 {len(detections)} 个元素",
    )
