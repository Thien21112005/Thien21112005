# Mekong Cyber — SVG Decoration Pack

Bộ trang trí SVG động cho GitHub Profile. Các file được thiết kế theo concept:
**Deep Navy + Electric Purple + Mekong Cyan**.

## Files

- `decorations/hero-mekong-cyber.svg` — banner đầu trang.
- `decorations/river-circuit.svg` — đường phân cách dạng dòng sông/dòng dữ liệu.
- `decorations/engineering-orbit.svg` — sơ đồ hệ sinh thái kỹ thuật.
- `decorations/terminal-card.svg` — thẻ terminal giới thiệu bản thân.

## Cách dùng trong README.md

Đặt banner ở đầu README, thay cho `background.jpg` nếu muốn:

```html
<div align="center">
  <img src="./decorations/hero-mekong-cyber.svg" width="100%" alt="Mekong Cyber banner" />
</div>
```

Dùng đường sông làm divider:

```html
<div align="center">
  <img src="./decorations/river-circuit.svg" width="100%" alt="River circuit divider" />
</div>
```

Dùng orbit ở khu vực giới thiệu kỹ năng:

```html
<div align="center">
  <img src="./decorations/engineering-orbit.svg" width="90%" alt="Engineering ecosystem" />
</div>
```

Dùng terminal card ở phần About Me:

```html
<div align="center">
  <img src="./decorations/terminal-card.svg" width="90%" alt="Developer terminal card" />
</div>
```

## Lưu ý về animation trên GitHub

Các SVG dùng animation SVG (SMIL), không cần JavaScript hay thư viện ngoài. GitHub có thể hiển thị SVG như ảnh tĩnh/động tùy cách phân phối và bộ lọc hiển thị. Nếu animation không chạy trong README preview, mở trực tiếp file SVG trên trình duyệt hoặc dùng ảnh GIF/WebP thay thế cho phần cần chuyển động.

Nên giữ khoảng 2–3 chi tiết động trong một README để profile không bị rối.
