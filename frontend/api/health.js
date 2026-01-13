export default function handler(request, response) {
    response.status(200).json({
        message: "Health check from FRONTEND api/health.js",
        time: new Date().toISOString()
    });
}
