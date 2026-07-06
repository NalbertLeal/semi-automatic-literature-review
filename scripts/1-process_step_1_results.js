deepseek_results = []
llama_results = []
qwen_results = []

function compute(a, b, c) {
    a_valid = []
    b_valid = []
    c_valid = []
    
    for (obj of a) {
        if (obj['final_label'] == 'VALID')  {
            try {
                a_valid.push( obj['prompt_txt_file'] )
            } catch (e) {
                console.log(obj['ERROR'])
            }
        }
    }
    
    for (obj of b) {
        if (obj['final_label'] == 'VALID')  {
            try {
                b_valid.push( obj['prompt_txt_file'] )
            } catch (e) {
                console.log(obj['ERROR'])
            }
        }
    }
    
    for (obj of c) {
        if (obj['final_label'] == 'VALID')  {
            try {
                c_valid.push( obj['prompt_txt_file'] )
            } catch (e) {
                console.log(obj['ERROR'])
            }
        }
    }
    
    a_set = new Set(a_valid)
    b_set = new Set(b_valid)
    c_set = new Set(c_valid)
    
    results_1 = a_set.intersection(b_set)
    results_2 = a_set.intersection(c_set)
    results_3 = b_set.intersection(c_set)
    
    return Array.from( results_1.union(results_2).union(results_3) )
}

console.log( compute(deepseek_results, llama_results, qwen_results) )