export function paramToTex(param: string): string {
    if (!param) return "";
    
    // Basic greek letters mapping
    let tex = param.replace(/mu/g, "\\mu ")
                   .replace(/alpha/g, "\\alpha ")
                   .replace(/beta/g, "\\beta ")
                   .replace(/sigma/g, "\\sigma ");
                   
    // Handle specific common bioprocess parameters (e.g. Y_X_S -> Y_{X/S})
    if (tex.includes("Y_") && tex.includes("_")) {
        const parts = param.split('_');
        if (parts.length === 3 && parts[0] === 'Y') {
            return `Y_{${parts[1]}/${parts[2]}}`;
        }
    }
    
    // Convert anything after first underscore to a subscript block
    if (tex.includes("_")) {
        const parts = tex.split("_");
        const base = parts[0];
        const sub = parts.slice(1).join("_");
        tex = `${base}_{${sub}}`;
    } else {
        // Handle trailing numbers (e.g. X0 -> X_0)
        tex = tex.replace(/([A-Za-z]+)(\d+)/g, "$1_{$2}");
    }
    
    return tex;
}
