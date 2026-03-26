mod lexer;
use lexer::tokenize;

fn main() {
    let tokens = tokenize("addi x1, x0, 42").unwrap();
    println!("Got {} tokens:", tokens.len());
    for (i, token) in tokens.iter().enumerate() {
        println!("  {}: {}", i, token);
    }
}
