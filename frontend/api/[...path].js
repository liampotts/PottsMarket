export const config = {
    runtime: 'edge',
};

export default async function handler(req) {
    const url = new URL(req.url);
    // Construct destination URL: keep pathname and query, switch origin to backend
    const targetUrl = new URL(url.pathname, 'https://pottsmarket-production.up.railway.app');
    targetUrl.search = url.search;

    // Prepare headers: Override Host to match backend expected host
    const headers = new Headers(req.headers);
    headers.set('host', 'pottsmarket-production.up.railway.app');

    // Forward the request
    try {
        const response = await fetch(targetUrl, {
            method: req.method,
            headers: headers,
            body: req.body,
            redirect: 'manual'
        });
        return response;
    } catch (error) {
        return new Response(JSON.stringify({ error: 'Proxy Failed', details: error.message }), { status: 500 });
    }
}
