const response = await fetch("https://kaysen-rupturable-marylyn.ngrok-free.dev/api/v1/fit", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "x-api-key": "my_secure_portal_token_123", // 보안키 필수!
        "ngrok-skip-browser-warning": "true"       // Ngrok 무료 버전 HTML 경고창 우회 헤더
    },
    body: JSON.stringify({
        "target_image_blob": "input/person/man2.jpg",
        "garment_image_blob": "input/cloth/standardKnit.jpg",
        "cloth_type": "upper"
    })
});

const data = await response.json();
console.log(data);
