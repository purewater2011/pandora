package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"strings"
)

func main() {
	listenSocket, err := net.Listen("tcp", "127.0.0.1:5710")
	if err != nil {
		fmt.Println("Error listening:", err.Error())
		os.Exit(1)
	}
	defer listenSocket.Close()

	fmt.Println("Listening on 127.0.0.1:5710")

	for {
		conn, err := listenSocket.Accept()
		if err != nil {
			fmt.Println("Error accepting connection:", err.Error())
			os.Exit(1)
		}
		go handleRequest(conn)
	}
}

func handleRequest(conn net.Conn) {
	buffer := make([]byte, 1024)
	_, err := conn.Read(buffer)
	if err != nil {
		fmt.Println("Error reading:", err.Error())
		conn.Close()
		return
	}

	request := string(buffer)
	fmt.Println(request)
	revJSON := extractRequestJSON(request)
	if revJSON != nil {
            fmt.Println(revJSON)
    }

	responseHeader := "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
	conn.Write([]byte(responseHeader))
	conn.Close()
}

func extractRequestJSON(request string) interface{} {
	// 根据两个空行切分请求
	requestParts := strings.Split(request, "\r\n\r\n")
	if len(requestParts) > 1 {
		payload := requestParts[len(requestParts)-1]
        payload = removeInvalidChars(payload)

		var jsonData map[string]interface{}
		err := json.Unmarshal([]byte(payload), &jsonData)
		if err != nil {
			fmt.Println("Error parsing JSON:", err)
			return nil
		}
		return jsonData
	}

	return nil
}

// 去除无效字符
func removeInvalidChars(str string) string {
	return strings.Map(func(r rune) rune {
		if r == '\x00' {
			return -1
		}
		return r
	}, str)
}

func requestToJSON(msg string) interface{} {
	for i := 0; i < len(msg); i++ {
		if msg[i] == '{' && msg[len(msg)-1] == '}' {
			var jsonData interface{}
			err := json.Unmarshal([]byte(msg[i:]), &jsonData)
			if err != nil {
				fmt.Println("Error parsing JSON:", err.Error())
				return nil
			}
			return jsonData
		}
	}
	return nil
}