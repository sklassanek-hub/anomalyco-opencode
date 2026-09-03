package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

func main() {
	client := openai.NewClient(
		option.WithBaseURL("http://127.0.0.1:1234/v1"),
		option.WithAPIKey("lm-studio"),
	)

	params := openai.ChatCompletionNewParams{
		Model: "mistralai/mistral-7b-instruct-v0.3",
		Messages: []openai.ChatCompletionMessageParamUnion{
			openai.UserMessage("Say hello"),
		},
		MaxTokens: openai.Int(100),
	}

	fmt.Println("=== Non-streaming ===")
	resp, err := client.Chat.Completions.New(context.Background(), params)
	if err != nil {
		log.Fatal(err)
	}
	data, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println(string(data))

	fmt.Println("\n=== Streaming ===")
	params.StreamOptions = openai.ChatCompletionStreamOptionsParam{
		IncludeUsage: openai.Bool(true),
	}
	stream := client.Chat.Completions.NewStreaming(context.Background(), params)
	for stream.Next() {
		chunk := stream.Current()
		data, _ := json.MarshalIndent(chunk, "", "  ")
		fmt.Println(string(data))
	}
	if err := stream.Err(); err != nil {
		log.Fatal(err)
	}
	fmt.Println("Stream completed")
}